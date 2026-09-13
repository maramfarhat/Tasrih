"""Tasrih — CIF + RNE + Fatoora → déclaration mensuelle officielle remplie."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from app.config import DATA, settings
from app import db
from app.declaration.extract import extract_cif, extract_rne, extract_invoice_file
from app.declaration.fatoora import authorize, create_auth_session, is_authorized
from app.declaration.fill_official import fill_official_pdf
from app.declaration.models import (
    BuildFromScansRequest,
    InvoiceExtract,
)
from app.declaration.pipeline import build_from_scans

UPLOADS = DATA / "uploads"
EXPORTS = DATA / "exports"
EMPLOYEE_DIR = UPLOADS / "employees"
UPLOADS.mkdir(parents=True, exist_ok=True)
EXPORTS.mkdir(parents=True, exist_ok=True)
EMPLOYEE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED = {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}
ALLOWED_INVOICE = ALLOWED | {".xml", ".xlms"}


def _save_upload(file: UploadFile, prefix: str, *, allowed: set[str] | None = None) -> Path:
    suffix = Path(file.filename or "doc.pdf").suffix.lower() or ".pdf"
    ok = allowed or ALLOWED
    if suffix not in ok:
        raise HTTPException(400, f"Formats autorisés: {', '.join(sorted(x.lstrip('.') for x in ok)).upper()}")
    dest = UPLOADS / f"{prefix}_{Path(file.filename or 'doc').stem}_{len(list(UPLOADS.glob('*')))}{suffix}"
    return dest


app = FastAPI(
    title="Tasrih Tunisie",
    description="Scan CIF + RNE + Fatoora → formulaire mensuel officiel rempli",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


def current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    user = db.user_from_token(token)
    if not user:
        raise HTTPException(401, "Connexion requise")
    return user


class RegisterBody(BaseModel):
    email: str
    password: str
    phone: str


class LoginBody(BaseModel):
    email: str
    password: str


class OnboardingBody(BaseModel):
    previous_is: str = ""
    has_personnel: bool | None = None
    declaration_channel: str = ""
    accountant_manages: bool | None = None


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "tasrih-tn",
        "version": "2.1.0",
        "groq_configured": bool(settings.groq_api_key),
        "official_template": (DATA / "templates" / "mensuelle2026.pdf").exists(),
    }


@app.post("/auth/register")
def auth_register(body: RegisterBody):
    try:
        user = db.create_user(body.email, body.password, body.phone)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    token = db.create_session(user["id"])
    return {"token": token, "user": user}


@app.post("/auth/login")
def auth_login(body: LoginBody):
    user = db.authenticate(body.email, body.password)
    if not user:
        raise HTTPException(401, "Email ou mot de passe incorrect")
    token = db.create_session(user["id"])
    return {"token": token, "user": user}


@app.get("/auth/me")
def auth_me(user: dict[str, Any] = Depends(current_user)):
    onboarding = db.get_onboarding(user["id"])
    return {
        "user": user,
        "onboarding": onboarding,
        "employees": db.list_employee_docs(user["id"]),
    }


@app.post("/auth/logout")
def auth_logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.lower().startswith("bearer "):
        db.delete_session(authorization.split(" ", 1)[1].strip())
    return {"ok": True}


@app.post("/onboarding")
def save_onboarding(body: OnboardingBody, user: dict[str, Any] = Depends(current_user)):
    saved = db.save_onboarding(user["id"], body.model_dump())
    return saved


@app.get("/onboarding")
def get_onboarding(user: dict[str, Any] = Depends(current_user)):
    return db.get_onboarding(user["id"]) or {}


@app.post("/employees/docs")
async def upload_employee_docs(
    employee_name: str = Form(...),
    contract: UploadFile | None = File(None),
    cnss: UploadFile | None = File(None),
    user: dict[str, Any] = Depends(current_user),
):
    if not employee_name.strip():
        raise HTTPException(400, "Nom de l'employé requis")
    if not contract and not cnss:
        raise HTTPException(400, "Ajoutez le contrat de travail et/ou la fiche CNSS")

    contract_path = None
    cnss_path = None
    uid = user["id"]

    if contract and contract.filename:
        dest = _save_upload(contract, f"emp{uid}_contract")
        dest.write_bytes(await contract.read())
        contract_path = str(dest)

    if cnss and cnss.filename:
        dest = _save_upload(cnss, f"emp{uid}_cnss")
        dest.write_bytes(await cnss.read())
        cnss_path = str(dest)

    doc = db.add_employee_doc(uid, employee_name, contract_path, cnss_path)
    return {"doc": doc, "employees": db.list_employee_docs(uid)}


@app.get("/employees/docs")
def list_employee_docs(user: dict[str, Any] = Depends(current_user)):
    return {"employees": db.list_employee_docs(user["id"])}


@app.post("/extract/cif")
async def api_extract_cif(file: UploadFile = File(...)):
    dest = _save_upload(file, "cif")
    dest.write_bytes(await file.read())
    try:
        return extract_cif(dest)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.post("/extract/rne")
async def api_extract_rne(file: UploadFile = File(...)):
    dest = _save_upload(file, "rne")
    dest.write_bytes(await file.read())
    try:
        return extract_rne(dest)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.post("/extract/invoice")
async def api_extract_invoice(file: UploadFile = File(...)):
    dest = _save_upload(file, "inv", allowed=ALLOWED_INVOICE)
    dest.write_bytes(await file.read())
    try:
        return extract_invoice_file(dest)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


@app.post("/fatoora/auth")
def fatoora_auth():
    return create_auth_session()


class FatooraAuthBody(BaseModel):
    token: str


@app.post("/fatoora/authorize")
def fatoora_authorize(body: FatooraAuthBody):
    return authorize(body.token)


@app.post("/fatoora/import-invoice")
async def fatoora_import(
    file: UploadFile = File(...),
    token: str = Form(...),
):
    if not is_authorized(token):
        raise HTTPException(401, "Autorisez Fatoora d'abord")
    dest = _save_upload(file, "fatoora", allowed=ALLOWED_INVOICE)
    dest.write_bytes(await file.read())
    try:
        return extract_invoice_file(dest)
    except Exception as exc:
        raise HTTPException(500, str(exc)) from exc


def _refresh_invoices(invoices: list[InvoiceExtract]) -> list[InvoiceExtract]:
    """Re-extrait depuis uploads si montants manquants (ancien scan en mémoire navigateur)."""
    debug: list[str] = []
    out: list[InvoiceExtract] = []
    for inv in invoices:
        needs = (
            inv.amount_ht is None
            or inv.amount_ht == 0
            or inv.vat_amount is None
            or inv.vat_amount == 0
            or (inv.stamp_duty or 0) >= 500
            or (inv.confidence or 0) < 0.55
        )
        debug.append(f"file={inv.filename} needs={needs} ht={inv.amount_ht} vat={inv.vat_amount} stamp={inv.stamp_duty} conf={inv.confidence}")
        if not needs:
            out.append(inv)
            continue
        stem = Path(inv.filename or "").stem
        candidates: list[Path] = []
        if stem:
            candidates = sorted(
                set(list(UPLOADS.glob(f"*{stem}*")) + list(UPLOADS.glob(f"*{stem[:40]}*"))),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
        if not candidates:
            candidates = sorted(
                list(UPLOADS.glob("inv_*")) + list(UPLOADS.glob("fatoora_*")),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[:3]
        debug.append(f"candidates={[c.name for c in candidates[:3]]}")
        if candidates:
            try:
                refreshed = extract_invoice_file(candidates[0])
                debug.append(f"refreshed ht={refreshed.amount_ht} conf={refreshed.confidence}")
                out.append(refreshed)
                continue
            except Exception as exc:
                debug.append(f"extract_err={exc}")
        out.append(inv)
    try:
        (DATA / "refresh_debug.txt").write_text("\n".join(debug), encoding="utf-8")
    except Exception:
        pass
    return out


@app.post("/pipeline/build")
def pipeline_build(req: BuildFromScansRequest):
    invoices = _refresh_invoices(req.invoices)
    return build_from_scans(
        month=req.month,
        cif=req.cif,
        rne=req.rne,
        invoices=invoices,
        answers=req.answers,
        amounts_override=req.amounts_override,
    )


@app.post("/pipeline/export-official")
def pipeline_export(req: BuildFromScansRequest):
    invoices = _refresh_invoices(req.invoices)
    filled = build_from_scans(
        month=req.month,
        cif=req.cif,
        rne=req.rne,
        invoices=invoices,
        answers=req.answers,
        amounts_override=req.amounts_override,
    )
    safe = "".join(c for c in (filled.profile.tax_id or "id") if c.isalnum() or c in "-_") or "id"
    out = EXPORTS / f"mensuelle_{filled.month.year}_{filled.month.month:02d}_{safe}.pdf"
    try:
        fill_official_pdf(filled, out)
    except Exception as exc:
        raise HTTPException(500, f"Export officiel: {exc}") from exc
    data = out.read_bytes()
    filename = f"mensuelle_{filled.month.year}_{filled.month.month:02d}.pdf"
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(len(data)),
        },
    )


# aliases legacy
@app.post("/extract-invoice")
async def legacy_extract(file: UploadFile = File(...)):
    return await api_extract_invoice(file)
