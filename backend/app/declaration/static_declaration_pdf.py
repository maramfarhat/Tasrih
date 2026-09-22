"""PDF statique de déclaration mensuelle — entièrement rempli (sans overlay décalé)."""

from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.declaration.models import FilledForm

FONT_PATHS = [
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
    Path(r"C:\Windows\Fonts\tahoma.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
]

CHECKBOX_LABELS_FR = {
    "خصم_من_المورد": "Retenue a la source",
    "الأداء_على_التكوين_المهني": "TFP",
    "صندوق_النهوض_بالمسكن": "FOPROLOS",
    "المعلوم_على_الاستهلاك": "Droit de consommation",
    "الأداء_على_القيمة_المضافة": "TVA",
    "معاليم_أخرى_على_رقم_المعاملات": "Autres droits sur CA",
    "معلوم_الطابع_الجبائي": "Droit de timbre",
    "المعلوم_على_المؤسسات": "Taxe etablissements",
    "المعلوم_على_النزل": "Taxe hotel",
    "معلوم_الإجازة": "Droit de licence",
}

_FONT = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"


def _ensure_fonts() -> tuple[str, str]:
    global _FONT, _FONT_BOLD
    if _FONT != "Helvetica" and _FONT in pdfmetrics.getRegisteredFontNames():
        return _FONT, _FONT_BOLD
    for path in FONT_PATHS:
        if not path.exists():
            continue
        try:
            pdfmetrics.registerFont(TTFont("TasrihDecl", str(path)))
            _FONT = "TasrihDecl"
            bold = path.with_name(path.stem.replace("arial", "arialbd") + path.suffix)
            if "arial" in path.name.lower() and Path(r"C:\Windows\Fonts\arialbd.ttf").exists():
                pdfmetrics.registerFont(TTFont("TasrihDeclBold", r"C:\Windows\Fonts\arialbd.ttf"))
                _FONT_BOLD = "TasrihDeclBold"
            else:
                _FONT_BOLD = _FONT
            return _FONT, _FONT_BOLD
        except Exception:
            continue
    _FONT, _FONT_BOLD = "Helvetica", "Helvetica-Bold"
    return _FONT, _FONT_BOLD


def _arab(text: str) -> str:
    if not text:
        return ""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)


def _txt(text: object) -> str:
    raw = "" if text is None else str(text)
    if not raw:
        return "—"
    if re.search(r"[\u0600-\u06FF]", raw):
        return _arab(raw)
    return raw


def _money(n: float | int | None) -> str:
    try:
        return f"{float(n or 0):,.3f}".replace(",", " ")
    except (TypeError, ValueError):
        return "0.000"


def export_static_declaration_pdf(filled: FilledForm, out_path: Path) -> Path:
    """Génère un PDF A4 lisible, prérempli avec toutes les données de la déclaration."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    font, font_bold = _ensure_fonts()
    c = canvas.Canvas(str(out_path), pagesize=A4)
    w, h = A4
    margin = 1.6 * cm
    y = h - margin

    def ensure_space(need: float = 1.2 * cm) -> None:
        nonlocal y
        if y < margin + need:
            c.showPage()
            y = h - margin

    def heading(title: str) -> None:
        nonlocal y
        ensure_space(1.4 * cm)
        c.setFillColor(colors.HexColor("#001f5c"))
        c.setFont(font_bold, 13)
        c.drawString(margin, y, title)
        y -= 0.35 * cm
        c.setStrokeColor(colors.HexColor("#0056b3"))
        c.setLineWidth(1.2)
        c.line(margin, y, w - margin, y)
        y -= 0.55 * cm
        c.setFillColor(colors.black)

    def row(label: str, value: object, size: int = 10) -> None:
        nonlocal y
        ensure_space(0.7 * cm)
        c.setFont(font_bold, size)
        c.setFillColor(colors.HexColor("#0056b3"))
        c.drawString(margin, y, label)
        c.setFillColor(colors.black)
        c.setFont(font, size)
        val = _txt(value)
        # wrap long values
        max_w = w - margin * 2 - 5.2 * cm
        words = val.split()
        lines: list[str] = []
        cur = ""
        for word in words:
            trial = f"{cur} {word}".strip()
            if c.stringWidth(trial, font, size) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        if not lines:
            lines = ["—"]
        c.drawString(margin + 5.2 * cm, y, lines[0][:120])
        y -= 0.48 * cm
        for extra in lines[1:]:
            ensure_space(0.5 * cm)
            c.drawString(margin + 5.2 * cm, y, extra[:120])
            y -= 0.45 * cm

    def money_row(label: str, value: float | int | None) -> None:
        row(label, f"{_money(value)} TND")

    p = filled.profile
    m = filled.month
    a = filled.amounts

    # —— En-tête
    c.setFillColor(colors.HexColor("#001f5c"))
    c.setFont(font_bold, 16)
    c.drawString(margin, y, "Tasrih — Declaration mensuelle")
    y -= 0.55 * cm
    c.setFont(font, 11)
    c.setFillColor(colors.HexColor("#004085"))
    c.drawString(margin, y, "Document statique pre-rempli (verification avant depot DGI)")
    y -= 0.35 * cm
    c.setStrokeColor(colors.HexColor("#001f5c"))
    c.setLineWidth(2)
    c.line(margin, y, w - margin, y)
    y -= 0.7 * cm
    c.setFillColor(colors.black)

    heading("1. Identite du contribuable")
    row("Raison sociale", p.name or p.commercial_name)
    row("Matricule fiscal", p.tax_id)
    row("Code TVA / categorie", f"{p.vat_code or '—'} / {p.category_code or '—'}")
    row("Etab. secondaire", p.secondary_establishment or "000")
    row("Statut TVA", p.vat_status or ("Assujetti A La TVA" if p.subject_to_vat else "Non Assujetti"))
    row("Identifiant RNE", p.rne_identifier)
    row("Forme juridique", p.legal_form)
    row("Nom commercial", p.commercial_name)
    row("Adresse", p.address)
    row("Activite", p.activity)
    row("Periode", f"{m.month:02d}/{m.year}  —  code {m.declaration_code.value}")

    heading("2. Rubriques fiscales (montants)")
    money_row("Chiffre d'affaires HT", a.ca_ht)
    money_row("Base TVA 19%", a.ca_ht_19)
    money_row("Base TVA 13%", a.ca_ht_13)
    money_row("Base TVA 7%", a.ca_ht_7)
    money_row("TVA collectee", a.tva_collectee)
    money_row("TVA deductible", a.tva_deductible)
    money_row("TVA nette / a payer", a.tva_nette)
    money_row("Credit TVA reporte", a.tva_credit_report)
    money_row("Credit TVA suivant", a.tva_credit_next)
    money_row("Retenue a la source", a.retenues_total)
    money_row("Base retenue", a.retenue_base_total)
    money_row("Masse salariale brute", a.masse_salariale_brute)
    money_row("TFP (assiette)", a.tfp_base)
    row("TFP (taux)", f"{(a.tfp_rate or 0) * 100:.0f} %")
    money_row("TFP (montant)", a.tfp_amount)
    money_row("FOPROLOS", a.foprolos_amount)
    row("Droit de timbre (nb)", str(a.stamp_duty_count or 0))
    money_row("Droit de timbre", a.stamp_duty_total)
    money_row("Taxe etablissements", a.etablissement_tax_amount)
    money_row("Taxe hotel", a.hotel_tax_amount)

    total_due = (
        max(0.0, float(a.tva_nette or 0))
        + max(0.0, float(a.retenues_total or 0))
        + max(0.0, float(a.tfp_amount or 0))
        + max(0.0, float(a.foprolos_amount or 0))
        + max(0.0, float(a.stamp_duty_total or 0))
        + max(0.0, float(a.etablissement_tax_amount or 0))
        + max(0.0, float(a.hotel_tax_amount or 0))
    )
    ensure_space(1.2 * cm)
    c.setFillColor(colors.HexColor("#e7eefb"))
    c.roundRect(margin, y - 0.35 * cm, w - 2 * margin, 0.9 * cm, 6, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#001f5c"))
    c.setFont(font_bold, 11)
    c.drawString(margin + 0.3 * cm, y, f"TOTAL A PAYER : {_money(total_due)} TND")
    y -= 1.1 * cm
    c.setFillColor(colors.black)

    heading("3. Taxes applicables")
    if filled.tax_lines:
        for t in filled.tax_lines:
            if isinstance(t, dict):
                label = t.get("label_fr") or t.get("key") or "Taxe"
                applicable = bool(t.get("applicable"))
            else:
                label = getattr(t, "label_fr", None) or getattr(t, "key", "Taxe")
                applicable = bool(getattr(t, "applicable", False))
            mark = "Applicable" if applicable else "Sans objet (X)"
            row(str(label), mark)
    else:
        for k, on in filled.checkboxes.items():
            if on:
                row(CHECKBOX_LABELS_FR.get(k, k), "Coche")

    heading("4. Factures (TEIF)")
    if filled.invoices:
        for inv in filled.invoices:
            row(
                inv.invoice_number or inv.filename or "Facture",
                f"HT {_money(inv.amount_ht)} · TVA {_money(inv.vat_amount)} · TTC {_money(inv.amount_ttc)}",
            )
    else:
        row("Factures", "Aucune")

    heading("5. Retenues a la source (TEJ)")
    if filled.retenues:
        for r in filled.retenues:
            row(
                r.beneficiary or r.certificate_number or "Beneficiaire",
                f"Base {_money(r.base)} · Taux {r.rate if r.rate is not None else '—'}% · {_money(r.amount)} TND",
            )
    else:
        row("Retenues", "Aucune")

    heading("6. Fiches de paie")
    if filled.payslips:
        for ps in filled.payslips:
            row(
                getattr(ps, "employee_name", None) or getattr(ps, "filename", None) or "Fiche",
                f"Brut {_money(getattr(ps, 'salaire_brut', None))}",
            )
    else:
        row("Paie", "Aucune / non scannee")

    ensure_space(2 * cm)
    y -= 0.3 * cm
    c.setFont(font, 8)
    c.setFillColor(colors.HexColor("#6c757d"))
    c.drawString(
        margin,
        y,
        "Document generique Tasrih — a verifier avant depot. Confiance: "
        f"{filled.confidence:.0%}.",
    )
    y -= 0.4 * cm
    c.drawString(margin, y, "Statut: en attente d'approbation DGI.")

    c.save()
    return out_path
