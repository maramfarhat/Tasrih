"""Routeur DGI (/admin) — vue administration fiscale, séparée du contribuable.

Auth : en-tête `X-Admin-Key` comparé à `settings.admin_password`.
Aucune donnée de cette vue n'est exposée au contribuable.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app import admin_db, db
from app.config import settings
from app.services import fraud

router = APIRouter(tags=["admin"])

MATERIAL_FIELDS = (
    "chiffre_affaires_declare",
    "tva_collectee",
    "tva_deductible",
    "retenue_totale",
)
EDIT_TOLERANCE_PCT = 5.0


# ————————————————————————— Auth —————————————————————————


def require_admin(x_admin_key: str | None = Header(default=None)) -> None:
    if not settings.admin_password or x_admin_key != settings.admin_password:
        raise HTTPException(401, "Accès administrateur requis")


def current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    user = db.user_from_token(token)
    if not user:
        raise HTTPException(401, "Connexion requise")
    return user


class AdminLogin(BaseModel):
    password: str


@router.post("/admin/login")
def admin_login(body: AdminLogin) -> dict[str, Any]:
    if not settings.admin_password or body.password != settings.admin_password:
        raise HTTPException(401, "Mot de passe administrateur invalide")
    return {"ok": True}


# ————————————————————————— Dashboard —————————————————————————


@router.get("/admin/dashboard", dependencies=[Depends(require_admin)])
def admin_dashboard(year: int | None = None, month: int | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    y = year or now.year
    m = month or now.month
    return admin_db.dashboard_stats(y, m)


# ————————————————————————— Businesses —————————————————————————


@router.get("/admin/businesses", dependencies=[Depends(require_admin)])
def admin_businesses(
    activite: str | None = None,
    regime: str | None = None,
    has_open_flags: bool | None = None,
    flag_severity: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    return admin_db.list_businesses(
        activite=activite,
        regime=regime,
        has_open_flags=has_open_flags,
        flag_severity=flag_severity,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/businesses/{business_id}", dependencies=[Depends(require_admin)])
def admin_business_detail(business_id: int) -> dict[str, Any]:
    business = admin_db.get_business(business_id)
    if not business:
        raise HTTPException(404, "Entreprise introuvable")
    return {
        "business": business,
        "declarations": admin_db.list_declarations(business_id),
        "flags": admin_db.list_flags(status=None, business_id=business_id),
        "field_edits": admin_db.list_field_edits_for_business(business_id),
    }


# ————————————————————————— Flags —————————————————————————


@router.get("/admin/flags", dependencies=[Depends(require_admin)])
def admin_flags(
    status: str | None = "open",
    severity: str | None = None,
    business_id: int | None = None,
) -> dict[str, Any]:
    return {"flags": admin_db.list_flags(status=status, severity=severity, business_id=business_id)}


class ReviewBody(BaseModel):
    status: str = Field(..., pattern="^(escalated|dismissed)$")
    note: str = ""


@router.post("/admin/flags/{flag_id}/review", dependencies=[Depends(require_admin)])
def admin_review_flag(flag_id: int, body: ReviewBody) -> dict[str, Any]:
    flag = admin_db.get_flag(flag_id)
    if not flag:
        raise HTTPException(404, "Drapeau introuvable")
    if not body.note.strip() and body.status == "escalated":
        raise HTTPException(422, "Une note est requise pour escalader un drapeau")
    updated = admin_db.review_flag(flag_id, body.status, body.note.strip(), reviewed_by="dgi")
    return {"flag": updated}


@router.post("/admin/run-detection", dependencies=[Depends(require_admin)])
def admin_run_detection() -> dict[str, Any]:
    return fraud.run_detection_all()


# ————————————————————— Contribuable : sauvegarde + édition —————————————————————


class SaveDeclarationBody(BaseModel):
    matricule_fiscal: str
    name: str = ""
    activite: str = ""
    code_tva: str = ""
    code_categorie: str = ""
    regime: str = "reel"
    month: int
    year: int
    chiffre_affaires_declare: float = 0
    tva_collectee: float = 0
    tva_deductible: float = 0
    retenue_totale: float = 0
    status: str = "prepared"
    invoice_count: int = 0
    invoice_amount_ht: float = 0
    invoice_amount_ttc: float = 0
    invoice_ids: list[str] = Field(default_factory=list)


@router.post("/declarations/save")
def save_declaration(
    body: SaveDeclarationBody, user: dict[str, Any] = Depends(current_user)
) -> dict[str, Any]:
    business_id = admin_db.upsert_business(
        matricule_fiscal=body.matricule_fiscal,
        code_tva=body.code_tva or None,
        code_categorie=body.code_categorie or None,
        activite=body.activite or None,
        regime=body.regime or None,
        name=body.name or None,
    )
    declaration_id = admin_db.upsert_declaration(
        business_id=business_id,
        month=body.month,
        year=body.year,
        chiffre_affaires_declare=body.chiffre_affaires_declare,
        tva_collectee=body.tva_collectee,
        tva_deductible=body.tva_deductible,
        retenue_totale=body.retenue_totale,
        status=body.status,
        date_submitted=datetime.now(timezone.utc).isoformat()
        if body.status in ("submitted", "paid")
        else None,
    )
    if body.invoice_count or body.invoice_amount_ht:
        admin_db.upsert_invoices_summary(
            business_id=business_id,
            month=body.month,
            year=body.year,
            total_invoice_count=body.invoice_count,
            total_invoice_amount_ht=body.invoice_amount_ht,
            total_invoice_amount_ttc=body.invoice_amount_ttc,
            invoice_ids=body.invoice_ids,
        )
    return {"business_id": business_id, "declaration_id": declaration_id}


class FieldEditBody(BaseModel):
    field_name: str
    ocr_extracted_value: float | str | None = None
    manual_value: float | str | None = None
    comment: str = ""


@router.post("/declarations/{declaration_id}/field-edit")
def declaration_field_edit(
    declaration_id: int,
    body: FieldEditBody,
    user: dict[str, Any] = Depends(current_user),
) -> dict[str, Any]:
    declaration = admin_db.get_declaration(declaration_id)
    if not declaration:
        raise HTTPException(404, "Déclaration introuvable")

    def _num(v: Any) -> float | None:
        try:
            return float(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None

    ocr = _num(body.ocr_extracted_value)
    manual = _num(body.manual_value)
    delta = 0.0
    if ocr is not None and manual is not None and ocr != 0:
        delta = (manual - ocr) / abs(ocr) * 100.0

    material = body.field_name in MATERIAL_FIELDS
    if material and abs(delta) > EDIT_TOLERANCE_PCT and not body.comment.strip():
        raise HTTPException(
            422,
            "Un motif est obligatoire pour modifier une valeur matérielle "
            f"(écart {delta:.1f}% > {EDIT_TOLERANCE_PCT:.0f}%).",
        )

    admin_db.add_field_edit(
        declaration_id=declaration_id,
        field_name=body.field_name,
        ocr_extracted_value=body.ocr_extracted_value,
        manual_value=body.manual_value,
        comment=body.comment.strip(),
    )
    # applique la valeur corrigée sur la déclaration
    patch = {**declaration}
    if body.field_name in MATERIAL_FIELDS and manual is not None:
        patch[body.field_name] = manual
        admin_db.upsert_declaration(
            business_id=declaration["business_id"],
            month=declaration["month"],
            year=declaration["year"],
            chiffre_affaires_declare=patch["chiffre_affaires_declare"],
            tva_collectee=patch["tva_collectee"],
            tva_deductible=patch["tva_deductible"],
            retenue_totale=patch["retenue_totale"],
            status=declaration["status"],
            date_submitted=declaration["date_submitted"],
        )
    return {"ok": True, "delta_percentage": round(delta, 2)}
