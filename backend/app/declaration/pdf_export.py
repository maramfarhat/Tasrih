from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

from app.declaration.models import FilledForm

# Libellés FR pour Helvetica (arabe brut = PDF illisible / corrompu)
CHECKBOX_LABELS_FR = {
    "خصم_من_المورد": "Retenues a la source",
    "الأداء_على_التكوين_المهني": "TFP",
    "صندوق_النهوض_بالمسكن": "FOPROLOS",
    "المعلوم_على_الاستهلاك": "Droit de consommation",
    "الأداء_على_القيمة_المضافة": "TVA",
    "معاليم_أخرى_على_رقم_المعاملات": "Autres droits sur CA",
    "معلوم_الطابع_الجبائي": "Droit de timbre",
    "المعلوم_على_المؤسسات": "Taxe sur les etablissements",
    "المعلوم_على_النزل": "Taxe hotel",
    "معلوم_الإجازة": "Taxe licence",
}


def _safe(txt: str) -> str:
    mapped = CHECKBOX_LABELS_FR.get(txt, txt)
    mapped = (
        mapped.replace("—", "-")
        .replace("–", "-")
        .replace("’", "'")
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ù", "u")
        .replace("ô", "o")
        .replace("î", "i")
        .replace("ç", "c")
    )
    return re.sub(r"[^\x20-\x7E]", "?", mapped)


def export_recap_pdf(filled: FilledForm, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(out_path), pagesize=A4)
    _w, h = A4
    y = h - 2 * cm

    def line(txt: str, size: int = 11, gap: float = 0.55) -> None:
        nonlocal y
        c.setFont("Helvetica", size)
        c.drawString(2 * cm, y, _safe(txt)[:110])
        y -= gap * cm
        if y < 2 * cm:
            c.showPage()
            y = h - 2 * cm

    p = filled.profile
    m = filled.month
    a = filled.amounts

    line("Tasrih - Declaration mensuelle (recap auto-rempli)", 14, 0.8)
    line(f"Periode: {m.month:02d}/{m.year}  |  Code declaration: {m.declaration_code.value}")
    line(f"Nom: {p.name}")
    line(f"Adresse: {p.address}  {p.postal_code}")
    line(f"Activite: {p.activity}")
    line(f"Identifiant fiscal: {p.tax_id}")
    line(f"Secteur: {p.sector.value}  |  Regime: {p.regime.value}")
    line("")
    line("Cases activees (x):", 12)
    for k, v in filled.checkboxes.items():
        if v:
            line(f"  [x] {CHECKBOX_LABELS_FR.get(k, k)}")
    line("")
    line("Montants:", 12)
    line(f"  CA HT: {a.ca_ht} TND")
    line(f"  TVA collectee: {a.tva_collectee} TND")
    line(f"  TVA deductible: {a.tva_deductible} TND")
    line(f"  TVA nette: {a.tva_nette} TND")
    line(f"  Retenues total: {a.retenues_total} TND")
    line(f"  Base hotel tax: {a.hotel_tax_base} | Montant: {a.hotel_tax_amount}")
    line(
        f"  Base etablissement: {a.etablissement_tax_base} | Montant: {a.etablissement_tax_amount}"
    )
    if a.other_notes:
        line(f"  Note: {a.other_notes}")
    line("")
    line(f"Confiance globale: {filled.confidence}", 12)
    if filled.needs_user_review:
        line("A verifier:", 12)
        for n in filled.needs_user_review:
            line(f"  - {n}")
    line("")
    line("Fatourat:", 12)
    for inv in filled.invoices:
        line(
            f"  - {inv.filename}: HT={inv.amount_ht} TVA={inv.vat_amount} TTC={inv.amount_ttc} ({inv.confidence})"
        )
    line("")
    line("Checklist:", 12)
    for item in filled.checklist:
        line(f"  [ ] {item}")
    line("")
    line("Disclaimer: assistant informatif - verification obligatoire avant depot.")
    c.save()
    return out_path
