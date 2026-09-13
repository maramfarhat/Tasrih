"""Base de connaissances Tasrih : guide officiel + référentiel fiscal + registre de champs.

Deux usages :
1. RAG : retrouver les passages du guide pour l'assistant (Karim) et la recherche.
2. Référentiel : taux, lignes de retenue, taxes, documents à fournir, et surtout le
   REGISTRE DES CHAMPS connus — pour mapper/valider/normaliser ce qui est extrait
   d'une photo (CIF, RNE, facture, fiche de paie).

La base est volontairement séparée de la base utilisateurs (tasrih.db).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from app.config import DATA

KB_PATH = DATA / "knowledge" / "knowledge.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS kb_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source_path TEXT,
    page_count INTEGER,
    text_hash TEXT,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS kb_sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    number TEXT,
    title TEXT,
    ordinal INTEGER,
    page INTEGER
);

CREATE TABLE IF NOT EXISTS kb_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES kb_documents(id) ON DELETE CASCADE,
    section_id INTEGER REFERENCES kb_sections(id) ON DELETE CASCADE,
    ordinal INTEGER,
    text TEXT NOT NULL
);

CREATE VIRTUAL TABLE IF NOT EXISTS kb_chunks_fts USING fts5(
    text,
    content='kb_chunks',
    content_rowid='id',
    tokenize='unicode61 remove_diacritics 2'
);

CREATE TRIGGER IF NOT EXISTS kb_chunks_ai AFTER INSERT ON kb_chunks BEGIN
    INSERT INTO kb_chunks_fts(rowid, text) VALUES (new.id, new.text);
END;
CREATE TRIGGER IF NOT EXISTS kb_chunks_ad AFTER DELETE ON kb_chunks BEGIN
    INSERT INTO kb_chunks_fts(kb_chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
END;
CREATE TRIGGER IF NOT EXISTS kb_chunks_au AFTER UPDATE ON kb_chunks BEGIN
    INSERT INTO kb_chunks_fts(kb_chunks_fts, rowid, text) VALUES ('delete', old.id, old.text);
    INSERT INTO kb_chunks_fts(rowid, text) VALUES (new.id, new.text);
END;

-- Référentiel fiscal -------------------------------------------------------
CREATE TABLE IF NOT EXISTS taxes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    name_fr TEXT NOT NULL,
    name_ar TEXT,
    section TEXT,
    base TEXT,
    rate TEXT,
    rate_value REAL,
    rate_unit TEXT,
    conditions TEXT,
    pieces TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS vat_rates (
    rate REAL PRIMARY KEY,
    label TEXT,
    category TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS withholding_lines (
    line_no INTEGER PRIMARY KEY,
    nature TEXT NOT NULL,
    base TEXT,
    rate TEXT,
    reference TEXT,
    pieces TEXT,
    source TEXT
);

CREATE TABLE IF NOT EXISTS required_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    item TEXT,
    notes TEXT
);

-- Registre des champs connus ------------------------------------------------
CREATE TABLE IF NOT EXISTS declaration_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_type TEXT NOT NULL,
    field_key TEXT NOT NULL,
    label_fr TEXT,
    label_ar TEXT,
    value_type TEXT,
    required INTEGER DEFAULT 0,
    enum_values TEXT,
    regex TEXT,
    model_path TEXT,
    description TEXT,
    UNIQUE(doc_type, field_key)
);

CREATE TABLE IF NOT EXISTS field_aliases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_type TEXT NOT NULL,
    field_key TEXT NOT NULL,
    alias TEXT NOT NULL,
    UNIQUE(doc_type, field_key, alias)
);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    KB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(KB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
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
        conn.executescript(SCHEMA)


def is_ready() -> bool:
    if not KB_PATH.exists():
        return False
    try:
        with connect() as conn:
            n = conn.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()[0]
            f = conn.execute("SELECT COUNT(*) FROM declaration_fields").fetchone()[0]
        return n > 0 and f > 0
    except sqlite3.Error:
        return False


def stats() -> dict[str, Any]:
    if not KB_PATH.exists():
        return {"ready": False}
    with connect() as conn:
        def count(table: str) -> int:
            try:
                return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            except sqlite3.Error:
                return 0

        return {
            "ready": True,
            "documents": count("kb_documents"),
            "sections": count("kb_sections"),
            "chunks": count("kb_chunks"),
            "taxes": count("taxes"),
            "vat_rates": count("vat_rates"),
            "withholding_lines": count("withholding_lines"),
            "required_documents": count("required_documents"),
            "declaration_fields": count("declaration_fields"),
            "field_aliases": count("field_aliases"),
        }
