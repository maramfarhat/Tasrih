"""Base de connaissances Tasrih (guide officiel + référentiel + registre de champs)."""

from __future__ import annotations

from pathlib import Path

from app.knowledge import db, search  # noqa: F401

__all__ = ["db", "search", "ensure_ready"]


def ensure_ready(pdf_path: Path | None = None) -> dict:
    """Ingère le guide si la base est vide/absente. Silencieux en cas d'échec."""
    from app.knowledge import ingest

    db.init_db()
    if db.is_ready():
        return {"ready": True, "ingested": False}
    target = pdf_path or ingest.DEFAULT_PDF
    if not target.exists():
        return {"ready": False, "ingested": False, "reason": "guide absent"}
    try:
        ingest.ingest(target)
        return {"ready": True, "ingested": True}
    except Exception as exc:  # pragma: no cover - démarrage tolérant
        return {"ready": False, "ingested": False, "reason": str(exc)}
