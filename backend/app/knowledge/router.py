"""Routes API de la base de connaissances."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.knowledge import db, ingest, search

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class ValidateBody(BaseModel):
    doc_type: str = Field(..., description="cif | rne | invoice | payslip | profile | amounts | form")
    values: dict[str, Any] = Field(default_factory=dict)


@router.get("/stats")
def knowledge_stats() -> dict[str, Any]:
    return db.stats()


@router.get("/search")
def knowledge_search(q: str, limit: int = 4) -> dict[str, Any]:
    limit = max(1, min(limit, 20))
    return {"query": q, "results": search.search_chunks(q, limit)}


@router.get("/fields")
def knowledge_fields(doc_type: str) -> dict[str, Any]:
    fields = search.known_fields(doc_type)
    if not fields:
        raise HTTPException(404, f"Type de document inconnu : {doc_type} (connus : {', '.join(search.all_doc_types())})")
    return {"doc_type": doc_type, "count": len(fields), "fields": fields}


@router.get("/reference")
def knowledge_reference() -> dict[str, Any]:
    return {
        "vat_rates": search.vat_rates(),
        "taxes": search.taxes(),
        "withholding_lines": search.withholding_lines(),
        "required_documents": search.required_documents(),
    }


@router.post("/validate")
def knowledge_validate(body: ValidateBody) -> dict[str, Any]:
    if not search.known_fields(body.doc_type):
        raise HTTPException(404, f"Type de document inconnu : {body.doc_type}")
    return search.validate_extraction(body.doc_type, body.values)


@router.post("/ingest")
def knowledge_ingest() -> dict[str, Any]:
    try:
        return ingest.ingest()
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc)) from exc
