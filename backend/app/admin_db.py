"""Persistence DGI (administration) : entreprises, déclarations, flags, éditions.

Séparé de la base contribuable (`db.py`) mais partage la même SQLite (`tasrih.db`)
et le même `connect()`. Alimente la vue /admin (jamais exposée au contribuable).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.db import connect


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_admin_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS businesses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matricule_fiscal TEXT NOT NULL UNIQUE,
                code_tva TEXT,
                code_categorie TEXT,
                activite TEXT,
                regime TEXT,
                name TEXT,
                date_registered TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS declarations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                chiffre_affaires_declare REAL DEFAULT 0,
                tva_collectee REAL DEFAULT 0,
                tva_deductible REAL DEFAULT 0,
                retenue_totale REAL DEFAULT 0,
                date_submitted TEXT,
                status TEXT NOT NULL DEFAULT 'prepared',
                created_at TEXT NOT NULL,
                UNIQUE (business_id, year, month)
            );

            CREATE TABLE IF NOT EXISTS invoices_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
                month INTEGER NOT NULL,
                year INTEGER NOT NULL,
                total_invoice_count INTEGER DEFAULT 0,
                total_invoice_amount_ht REAL DEFAULT 0,
                total_invoice_amount_ttc REAL DEFAULT 0,
                invoice_ids_json TEXT,
                UNIQUE (business_id, year, month)
            );

            CREATE TABLE IF NOT EXISTS field_edits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                declaration_id INTEGER NOT NULL REFERENCES declarations(id) ON DELETE CASCADE,
                field_name TEXT NOT NULL,
                ocr_extracted_value TEXT,
                manual_value TEXT,
                comment TEXT,
                edited_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS risk_flags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id INTEGER NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
                declaration_id INTEGER REFERENCES declarations(id) ON DELETE CASCADE,
                flag_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                explanation TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                reviewed_by TEXT,
                reviewed_at TEXT,
                resolution_note TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_flags_status ON risk_flags(status);
            CREATE INDEX IF NOT EXISTS idx_flags_sev ON risk_flags(severity);
            CREATE INDEX IF NOT EXISTS idx_decl_biz ON declarations(business_id, year, month);
            """
        )


# ————————————————————————— Businesses —————————————————————————


def upsert_business(
    matricule_fiscal: str,
    code_tva: str | None = None,
    code_categorie: str | None = None,
    activite: str | None = None,
    regime: str | None = None,
    name: str | None = None,
    date_registered: str | None = None,
) -> int:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO businesses (matricule_fiscal, code_tva, code_categorie, activite, regime, name, date_registered, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(matricule_fiscal) DO UPDATE SET
                code_tva = COALESCE(excluded.code_tva, businesses.code_tva),
                code_categorie = COALESCE(excluded.code_categorie, businesses.code_categorie),
                activite = COALESCE(excluded.activite, businesses.activite),
                regime = COALESCE(excluded.regime, businesses.regime),
                name = COALESCE(excluded.name, businesses.name),
                date_registered = COALESCE(excluded.date_registered, businesses.date_registered)
            """,
            (
                matricule_fiscal,
                code_tva,
                code_categorie,
                activite,
                regime,
                name,
                date_registered,
                _utcnow(),
            ),
        )
        row = conn.execute(
            "SELECT id FROM businesses WHERE matricule_fiscal = ?", (matricule_fiscal,)
        ).fetchone()
    return int(row["id"])


def _business_row(r) -> dict[str, Any]:
    return {
        "id": r["id"],
        "matricule_fiscal": r["matricule_fiscal"],
        "code_tva": r["code_tva"],
        "code_categorie": r["code_categorie"],
        "activite": r["activite"],
        "regime": r["regime"],
        "name": r["name"],
        "date_registered": r["date_registered"],
    }


def list_businesses(
    activite: str | None = None,
    regime: str | None = None,
    has_open_flags: bool | None = None,
    flag_severity: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    where: list[str] = []
    params: list[Any] = []
    if activite:
        where.append("b.activite LIKE ?")
        params.append(f"%{activite}%")
    if regime:
        where.append("b.regime = ?")
        params.append(regime)
    if has_open_flags is not None:
        op = "EXISTS" if has_open_flags else "NOT EXISTS"
        where.append(
            f"{op} (SELECT 1 FROM risk_flags f WHERE f.business_id = b.id AND f.status = 'open')"
        )
    if flag_severity:
        where.append(
            "EXISTS (SELECT 1 FROM risk_flags f WHERE f.business_id = b.id "
            "AND f.status = 'open' AND f.severity = ?)"
        )
        params.append(flag_severity)
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    with connect() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM businesses b {clause}", params
        ).fetchone()["n"]
        rows = conn.execute(
            f"""
            SELECT b.*,
              (SELECT status FROM declarations d WHERE d.business_id = b.id
                 ORDER BY d.year DESC, d.month DESC LIMIT 1) AS latest_status,
              (SELECT year FROM declarations d WHERE d.business_id = b.id
                 ORDER BY d.year DESC, d.month DESC LIMIT 1) AS latest_year,
              (SELECT month FROM declarations d WHERE d.business_id = b.id
                 ORDER BY d.year DESC, d.month DESC LIMIT 1) AS latest_month,
              (SELECT COUNT(*) FROM risk_flags f WHERE f.business_id = b.id AND f.status='open') AS open_flags,
              (SELECT severity FROM risk_flags f WHERE f.business_id = b.id AND f.status='open'
                 ORDER BY CASE f.severity WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END DESC
                 LIMIT 1) AS max_severity
            FROM businesses b
            {clause}
            ORDER BY b.name COLLATE NOCASE
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, (max(1, page) - 1) * page_size],
        ).fetchall()
    items = []
    for r in rows:
        item = _business_row(r)
        item.update(
            {
                "latest_status": r["latest_status"],
                "latest_period": (
                    f"{r['latest_month']:02d}/{r['latest_year']}"
                    if r["latest_month"] and r["latest_year"]
                    else None
                ),
                "open_flags": r["open_flags"],
                "max_severity": r["max_severity"],
            }
        )
        items.append(item)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def get_business(business_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM businesses WHERE id = ?", (business_id,)).fetchone()
    return _business_row(row) if row else None


# ————————————————————————— Declarations —————————————————————————


def upsert_declaration(
    business_id: int,
    month: int,
    year: int,
    chiffre_affaires_declare: float = 0,
    tva_collectee: float = 0,
    tva_deductible: float = 0,
    retenue_totale: float = 0,
    date_submitted: str | None = None,
    status: str = "prepared",
) -> int:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO declarations (business_id, month, year, chiffre_affaires_declare, tva_collectee, tva_deductible, retenue_totale, date_submitted, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(business_id, year, month) DO UPDATE SET
                chiffre_affaires_declare = excluded.chiffre_affaires_declare,
                tva_collectee = excluded.tva_collectee,
                tva_deductible = excluded.tva_deductible,
                retenue_totale = excluded.retenue_totale,
                date_submitted = COALESCE(excluded.date_submitted, declarations.date_submitted),
                status = excluded.status
            """,
            (
                business_id,
                month,
                year,
                chiffre_affaires_declare,
                tva_collectee,
                tva_deductible,
                retenue_totale,
                date_submitted,
                status,
                _utcnow(),
            ),
        )
        row = conn.execute(
            "SELECT id FROM declarations WHERE business_id = ? AND year = ? AND month = ?",
            (business_id, year, month),
        ).fetchone()
    return int(row["id"])


def _declaration_row(r) -> dict[str, Any]:
    return {
        "id": r["id"],
        "business_id": r["business_id"],
        "month": r["month"],
        "year": r["year"],
        "chiffre_affaires_declare": r["chiffre_affaires_declare"],
        "tva_collectee": r["tva_collectee"],
        "tva_deductible": r["tva_deductible"],
        "retenue_totale": r["retenue_totale"],
        "date_submitted": r["date_submitted"],
        "status": r["status"],
    }


def get_declaration(declaration_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM declarations WHERE id = ?", (declaration_id,)).fetchone()
    return _declaration_row(row) if row else None


def list_declarations(business_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM declarations WHERE business_id = ? ORDER BY year DESC, month DESC",
            (business_id,),
        ).fetchall()
    return [_declaration_row(r) for r in rows]


def declaration_for_period(business_id: int, year: int, month: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM declarations WHERE business_id = ? AND year = ? AND month = ?",
            (business_id, year, month),
        ).fetchone()
    return _declaration_row(row) if row else None


def list_all_declarations(limit: int = 5000) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM declarations ORDER BY year DESC, month DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_declaration_row(r) for r in rows]


# ————————————————————————— Invoices summary —————————————————————————


def upsert_invoices_summary(
    business_id: int,
    month: int,
    year: int,
    total_invoice_count: int,
    total_invoice_amount_ht: float,
    total_invoice_amount_ttc: float,
    invoice_ids: list[str] | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO invoices_summary (business_id, month, year, total_invoice_count, total_invoice_amount_ht, total_invoice_amount_ttc, invoice_ids_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(business_id, year, month) DO UPDATE SET
                total_invoice_count = excluded.total_invoice_count,
                total_invoice_amount_ht = excluded.total_invoice_amount_ht,
                total_invoice_amount_ttc = excluded.total_invoice_amount_ttc,
                invoice_ids_json = excluded.invoice_ids_json
            """,
            (
                business_id,
                month,
                year,
                total_invoice_count,
                total_invoice_amount_ht,
                total_invoice_amount_ttc,
                json.dumps(invoice_ids or [], ensure_ascii=False),
            ),
        )


def get_invoices_summary(business_id: int, year: int, month: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM invoices_summary WHERE business_id = ? AND year = ? AND month = ?",
            (business_id, year, month),
        ).fetchone()
    if not row:
        return None
    return {
        "business_id": row["business_id"],
        "month": row["month"],
        "year": row["year"],
        "total_invoice_count": row["total_invoice_count"],
        "total_invoice_amount_ht": row["total_invoice_amount_ht"],
        "total_invoice_amount_ttc": row["total_invoice_amount_ttc"],
        "invoice_ids": json.loads(row["invoice_ids_json"] or "[]"),
    }


# ————————————————————————— Field edits —————————————————————————


def add_field_edit(
    declaration_id: int,
    field_name: str,
    ocr_extracted_value: Any,
    manual_value: Any,
    comment: str,
) -> dict[str, Any]:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO field_edits (declaration_id, field_name, ocr_extracted_value, manual_value, comment, edited_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                declaration_id,
                field_name,
                None if ocr_extracted_value is None else str(ocr_extracted_value),
                None if manual_value is None else str(manual_value),
                comment,
                _utcnow(),
            ),
        )
        edit_id = int(cur.lastrowid)
    return {"id": edit_id, "declaration_id": declaration_id, "field_name": field_name}


def list_field_edits(declaration_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM field_edits WHERE declaration_id = ? ORDER BY edited_at DESC",
            (declaration_id,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "declaration_id": r["declaration_id"],
            "field_name": r["field_name"],
            "ocr_extracted_value": r["ocr_extracted_value"],
            "manual_value": r["manual_value"],
            "comment": r["comment"],
            "edited_at": r["edited_at"],
        }
        for r in rows
    ]


def list_field_edits_for_business(business_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT fe.*, d.year, d.month
            FROM field_edits fe
            JOIN declarations d ON d.id = fe.declaration_id
            WHERE d.business_id = ?
            ORDER BY fe.edited_at DESC
            """,
            (business_id,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "declaration_id": r["declaration_id"],
            "field_name": r["field_name"],
            "ocr_extracted_value": r["ocr_extracted_value"],
            "manual_value": r["manual_value"],
            "comment": r["comment"],
            "edited_at": r["edited_at"],
            "period": f"{r['month']:02d}/{r['year']}",
        }
        for r in rows
    ]


# ————————————————————————— Risk flags —————————————————————————


def add_flag(
    business_id: int,
    declaration_id: int | None,
    flag_type: str,
    severity: str,
    evidence: dict[str, Any],
    explanation: str,
) -> int:
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO risk_flags (business_id, declaration_id, flag_type, severity, evidence_json, explanation, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
            """,
            (
                business_id,
                declaration_id,
                flag_type,
                severity,
                json.dumps(evidence, ensure_ascii=False),
                explanation,
                _utcnow(),
            ),
        )
        return int(cur.lastrowid)


def clear_open_flags_for_declaration(declaration_id: int) -> None:
    """Avant de relancer la détection : on retire les drapeaux ouverts de ce mois
    (pour éviter les doublons). Les drapeaux déjà traités sont conservés."""
    with connect() as conn:
        conn.execute(
            "DELETE FROM risk_flags WHERE declaration_id = ? AND status = 'open'",
            (declaration_id,),
        )


def _flag_row(r) -> dict[str, Any]:
    return {
        "id": r["id"],
        "business_id": r["business_id"],
        "declaration_id": r["declaration_id"],
        "flag_type": r["flag_type"],
        "severity": r["severity"],
        "evidence": json.loads(r["evidence_json"] or "{}"),
        "explanation": r["explanation"],
        "status": r["status"],
        "reviewed_by": r["reviewed_by"],
        "reviewed_at": r["reviewed_at"],
        "resolution_note": r["resolution_note"],
        "created_at": r["created_at"],
    }


_SEV_ORDER = "CASE f.severity WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END"


def list_flags(
    status: str | None = "open",
    severity: str | None = None,
    business_id: int | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if status:
        where.append("f.status = ?")
        params.append(status)
    if severity:
        where.append("f.severity = ?")
        params.append(severity)
    if business_id:
        where.append("f.business_id = ?")
        params.append(business_id)
    clause = ("WHERE " + " AND ".join(where)) if where else ""
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT f.*, b.name AS business_name, b.matricule_fiscal, b.activite,
                   d.month AS decl_month, d.year AS decl_year
            FROM risk_flags f
            JOIN businesses b ON b.id = f.business_id
            LEFT JOIN declarations d ON d.id = f.declaration_id
            {clause}
            ORDER BY {_SEV_ORDER} DESC, f.created_at DESC
            LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
    out = []
    for r in rows:
        item = _flag_row(r)
        item.update(
            {
                "business_name": r["business_name"],
                "matricule_fiscal": r["matricule_fiscal"],
                "activite": r["activite"],
                "period": (
                    f"{r['decl_month']:02d}/{r['decl_year']}"
                    if r["decl_month"] and r["decl_year"]
                    else None
                ),
            }
        )
        out.append(item)
    return out


def get_flag(flag_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM risk_flags WHERE id = ?", (flag_id,)).fetchone()
    return _flag_row(row) if row else None


def review_flag(flag_id: int, status: str, note: str, reviewed_by: str = "dgi") -> dict[str, Any] | None:
    with connect() as conn:
        conn.execute(
            """
            UPDATE risk_flags
            SET status = ?, resolution_note = ?, reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
            """,
            (status, note, reviewed_by, _utcnow(), flag_id),
        )
    return get_flag(flag_id)


# ————————————————————————— Dashboard —————————————————————————


def dashboard_stats(year: int, month: int) -> dict[str, Any]:
    with connect() as conn:
        total_businesses = conn.execute("SELECT COUNT(*) AS n FROM businesses").fetchone()["n"]
        status_rows = conn.execute(
            """
            SELECT status, COUNT(*) AS n FROM declarations
            WHERE year = ? AND month = ? GROUP BY status
            """,
            (year, month),
        ).fetchall()
        submitted = conn.execute(
            """
            SELECT COUNT(*) AS n FROM declarations
            WHERE year = ? AND month = ? AND status IN ('submitted','paid')
            """,
            (year, month),
        ).fetchone()["n"]
        sev_rows = conn.execute(
            """
            SELECT severity, COUNT(*) AS n FROM risk_flags
            WHERE status = 'open' GROUP BY severity
            """,
        ).fetchall()
        by_activity = conn.execute(
            """
            SELECT COALESCE(b.activite, 'Non précisé') AS activite, COUNT(*) AS n
            FROM risk_flags f JOIN businesses b ON b.id = f.business_id
            WHERE f.status = 'open'
            GROUP BY COALESCE(b.activite, 'Non précisé')
            ORDER BY n DESC
            """,
        ).fetchall()
    status_counts = {row["status"]: row["n"] for row in status_rows}
    severity_counts = {row["severity"]: row["n"] for row in sev_rows}
    expected = total_businesses
    return {
        "period": {"year": year, "month": month},
        "suivi": {
            "expected": expected,
            "submitted": submitted,
            "late": max(0, expected - submitted),
            "submitted_pct": round(submitted / expected * 100, 1) if expected else 0.0,
        },
        "etat": {
            "prepared": status_counts.get("prepared", 0),
            "submitted": status_counts.get("submitted", 0),
            "paid": status_counts.get("paid", 0),
            "late": max(0, expected - submitted),
        },
        "flags": {
            "high": severity_counts.get("high", 0),
            "medium": severity_counts.get("medium", 0),
            "low": severity_counts.get("low", 0),
            "total": sum(severity_counts.values()),
        },
        "flags_by_activity": [
            {"activite": r["activite"], "count": r["n"]} for r in by_activity
        ],
    }
