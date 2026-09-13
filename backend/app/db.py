"""SQLite persistence for users, onboarding answers, and employee documents."""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import DATA

DB_PATH = DATA / "tasrih.db"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return salt, digest.hex()


def verify_password(password: str, salt: str, hashed: str) -> bool:
    _, digest = _hash_password(password, salt)
    return secrets.compare_digest(digest, hashed)


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                phone TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS onboarding (
                user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                previous_is TEXT,
                has_personnel INTEGER,
                declaration_channel TEXT,
                accountant_manages INTEGER,
                answers_json TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS employee_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                employee_name TEXT NOT NULL,
                contract_path TEXT,
                cnss_path TEXT,
                created_at TEXT NOT NULL
            );
            """
        )


def create_user(email: str, password: str, phone: str) -> dict[str, Any]:
    email = email.strip().lower()
    phone = phone.strip()
    if not email or not password or not phone:
        raise ValueError("Email, mot de passe et téléphone sont requis")
    if len(password) < 6:
        raise ValueError("Mot de passe trop court (min. 6 caractères)")
    salt, hashed = _hash_password(password)
    with connect() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise ValueError("Un compte existe déjà avec cet email")
        cur = conn.execute(
            "INSERT INTO users (email, phone, password_salt, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (email, phone, salt, hashed, _utcnow()),
        )
        user_id = int(cur.lastrowid)
    return {"id": user_id, "email": email, "phone": phone}


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    email = email.strip().lower()
    with connect() as conn:
        row = conn.execute(
            "SELECT id, email, phone, password_salt, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
    if not row:
        return None
    if not verify_password(password, row["password_salt"], row["password_hash"]):
        return None
    return {"id": row["id"], "email": row["email"], "phone": row["phone"]}


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, _utcnow()),
        )
    return token


def user_from_token(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    with connect() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.email, u.phone
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
    if not row:
        return None
    return {"id": row["id"], "email": row["email"], "phone": row["phone"]}


def delete_session(token: str) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))


def save_onboarding(user_id: int, answers: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "previous_is": str(answers.get("previous_is") or ""),
        "has_personnel": 1 if answers.get("has_personnel") is True else 0 if answers.get("has_personnel") is False else None,
        "declaration_channel": str(answers.get("declaration_channel") or ""),
        "accountant_manages": 1
        if answers.get("accountant_manages") is True
        else 0
        if answers.get("accountant_manages") is False
        else None,
        "answers_json": json.dumps(answers, ensure_ascii=False),
        "updated_at": _utcnow(),
    }
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO onboarding (user_id, previous_is, has_personnel, declaration_channel, accountant_manages, answers_json, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                previous_is = excluded.previous_is,
                has_personnel = excluded.has_personnel,
                declaration_channel = excluded.declaration_channel,
                accountant_manages = excluded.accountant_manages,
                answers_json = excluded.answers_json,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                payload["previous_is"],
                payload["has_personnel"],
                payload["declaration_channel"],
                payload["accountant_manages"],
                payload["answers_json"],
                payload["updated_at"],
            ),
        )
    return get_onboarding(user_id) or {}


def get_onboarding(user_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM onboarding WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return None
    has_p = row["has_personnel"]
    acc = row["accountant_manages"]
    return {
        "previous_is": row["previous_is"] or "",
        "has_personnel": None if has_p is None else bool(has_p),
        "declaration_channel": row["declaration_channel"] or "",
        "accountant_manages": None if acc is None else bool(acc),
        "answers": json.loads(row["answers_json"] or "{}"),
        "updated_at": row["updated_at"],
    }


def add_employee_doc(
    user_id: int,
    employee_name: str,
    contract_path: str | None,
    cnss_path: str | None,
) -> dict[str, Any]:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO employee_docs (user_id, employee_name, contract_path, cnss_path, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, employee_name.strip(), contract_path, cnss_path, _utcnow()),
        )
        doc_id = int(cur.lastrowid)
    return {
        "id": doc_id,
        "employee_name": employee_name.strip(),
        "contract_path": contract_path,
        "cnss_path": cnss_path,
    }


def list_employee_docs(user_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, employee_name, contract_path, cnss_path, created_at
            FROM employee_docs WHERE user_id = ? ORDER BY id DESC
            """,
            (user_id,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "employee_name": r["employee_name"],
            "has_contract": bool(r["contract_path"]),
            "has_cnss": bool(r["cnss_path"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]
