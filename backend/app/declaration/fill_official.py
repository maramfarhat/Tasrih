"""Remplit le PDF officiel mensuelle2026.pdf (12 pages) par overlay — sans modifier le gabarit."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.config import BACKEND
from app.declaration.models import FilledForm

TEMPLATE = BACKEND / "data" / "templates" / "mensuelle2026.pdf"
_TEMPLATE_FALLBACKS = [
    Path(r"C:\Users\maram\Downloads\mensuelle2026.pdf"),
    BACKEND.parent / "docs" / "declaration-mensuelle" / "imprime-officiel-2025.pdf",
]
FONT_PATHS = [
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path(r"C:\Windows\Fonts\tahoma.ttf"),
    Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]

# Texte ajouté en rouge (lisible sur le gabarit officiel).
FILL_COLOR = colors.Color(0.78, 0.0, 0.0)

_FONT = "Helvetica"


def _ensure_font() -> str:
    global _FONT
    if _FONT != "Helvetica" and _FONT in pdfmetrics.getRegisteredFontNames():
        return _FONT
    for path in FONT_PATHS:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("TasrihFont", str(path)))
                _FONT = "TasrihFont"
                return _FONT
            except Exception:
                continue
    _FONT = "Helvetica"
    return _FONT


def _arab(text: str) -> str:
    if not text:
        return ""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)


def _safe_draw_text(text: str, rtl: bool = False) -> str:
    raw = str(text or "")
    if not raw:
        return ""
    has_ar = bool(re.search(r"[\u0600-\u06FF]", raw))
    s = _arab(raw) if (rtl or has_ar) else raw
    if _FONT != "Helvetica":
        return s[:90]
    try:
        s.encode("latin-1")
        return s[:90]
    except UnicodeEncodeError:
        return "".join(ch if ord(ch) < 256 else "?" for ch in raw)[:90]


def _ink(c: canvas.Canvas) -> None:
    c.setFillColor(FILL_COLOR)


def _draw(c: canvas.Canvas, x: float, y: float, text: str, size: float = 9, rtl: bool = False) -> None:
    if text is None or str(text).strip() == "":
        return
    font = _ensure_font()
    _ink(c)
    c.setFont(font, size)
    s = _safe_draw_text(str(text), rtl=rtl)
    try:
        c.drawString(x, y, s[:90])
    except Exception:
        c.setFont("Helvetica", size)
        ascii_s = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in str(text))[:90]
        c.drawString(x, y, ascii_s)


def _draw_boxes(
    c: canvas.Canvas,
    x: float,
    y: float,
    text: str,
    spacing: float = 13,
    size: float = 10,
) -> None:
    """Un caractère centré dans chaque case."""
    font = _ensure_font()
    _ink(c)
    c.setFont(font, size)
    cleaned = re.sub(r"\s+", "", str(text or ""))
    for i, ch in enumerate(cleaned[:24]):
        try:
            c.drawString(x + i * spacing, y, ch)
        except Exception:
            c.setFont("Helvetica", size)
            if 32 <= ord(ch) < 127:
                c.drawString(x + i * spacing, y, ch)


def _mark(c: canvas.Canvas, x: float, y: float, on: bool) -> None:
    if not on:
        return
    _ink(c)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "X")


def _mark_x(c: canvas.Canvas, x: float, y: float) -> None:
    _ink(c)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x, y, "X")


def _fmt(n: float | int | None) -> str:
    try:
        return f"{float(n or 0):.3f}"
    except (TypeError, ValueError):
        return "0.000"


def _clean_address(address: str) -> tuple[str, str]:
    raw = re.sub(r"\s+", " ", (address or "").strip())
    raw = re.sub(r"\bsign\b", "", raw, flags=re.I).strip(" ,+")
    postal = ""
    m = re.search(r"\b(\d{4})\b", raw)
    if m:
        postal = m.group(1)
        raw = re.sub(rf"\b{postal}\b", "", raw).strip(" ,+")
    return raw, postal


def _split_tax_id(tax_id: str) -> tuple[str, str]:
    """1290021/A → ('1290021', 'A')."""
    raw = re.sub(r"\s+", "", tax_id or "").upper()
    if "/" in raw:
        left, right = raw.split("/", 1)
        return re.sub(r"\D", "", left), re.sub(r"[^A-Z]", "", right)[:1]
    return re.sub(r"\D", "", raw), re.sub(r"[^A-Z]", "", raw)[:1]


def _page1_overlay(filled: FilledForm) -> bytes:
    """Page 1 — valeurs en rouge, calées sur les labels du mensuelle2026.pdf."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    p = filled.profile
    m = filled.month
    boxes = filled.checkboxes
    a = filled.amounts

    # —— Année / mois / code : MÊME ligne que libellés y≈720.6 (pas la ligne matricule)
    # السنة@155 · الشهر@256 · رمز@336 — cases à gauche de chaque libellé
    _draw_boxes(c, 98, 718, f"{m.year:04d}", spacing=13.2, size=10)
    _draw_boxes(c, 220, 718, f"{m.month:02d}", spacing=13.2, size=10)
    _draw_boxes(c, 310, 718, str(m.declaration_code.value), spacing=13.2, size=10)

    # —— Matricule : cases sous المعرف الجبائي (labels ≈698 → cases ≈680)
    digits, key = _split_tax_id(p.tax_id or "")
    etab = re.sub(r"\D", "", p.secondary_establishment or "000")[:3].zfill(3)
    cat = (p.category_code or "")[:1].upper()
    vat = (p.vat_code or "")[:1].upper()
    y_tax = 680
    _draw_boxes(c, 48, y_tax, etab, spacing=11.5, size=9)
    _draw(c, 90, y_tax, cat, 9)
    _draw(c, 115, y_tax, vat, 9)
    _draw_boxes(c, 175, y_tax, digits[:7], spacing=12.5, size=9)
    x_slash = 175 + 12.5 * min(7, len(digits[:7]))
    _draw(c, x_slash + 1, y_tax, "/", 9)
    if key:
        _draw(c, x_slash + 12, y_tax, key, 9)

    # —— Identité
    name = (p.name or p.commercial_name or "")[:50]
    addr, postal = _clean_address(p.address or "")
    if not postal and p.postal_code:
        postal = re.sub(r"\D", "", p.postal_code)[:4]
    addr = re.sub(r"^0{2,3}\s*", "", addr).strip(" ,+")[:60]

    _draw(c, 48, 656, name, 9)
    _draw(c, 48, 643, addr, 8)
    if postal:
        _draw_boxes(c, 48, 630, postal[:4], spacing=12.5, size=9)

    # —— Activité : pointillés النشاط seulement (x≈300–420).
    # Ne jamais écrire sur تاريخ توقيف / اليوم / الشهر / السنة.
    _draw(c, 300, 616, (p.activity or "")[:28], 8)

    # —— Cases type d'impôt
    _mark(c, 512, 522, boxes.get("خصم_من_المورد", False))
    _mark(c, 455, 522, boxes.get("الأداء_على_التكوين_المهني", False))
    _mark(c, 388, 522, boxes.get("صندوق_النهوض_بالمسكن", False))
    _mark(c, 330, 522, boxes.get("المعلوم_على_الاستهلاك", False))
    _mark(c, 275, 522, boxes.get("الأداء_على_القيمة_المضافة", False))
    _mark(c, 212, 522, boxes.get("معاليم_أخرى_على_رقم_المعاملات", False))
    _mark(c, 165, 522, boxes.get("معلوم_الطابع_الجبائي", False))
    _mark(c, 112, 522, boxes.get("المعلوم_على_المؤسسات", False))
    _mark(c, 70, 522, boxes.get("المعلوم_على_النزل", False))
    _mark(c, 35, 522, boxes.get("معلوم_الإجازة", False))

    if boxes.get("خصم_من_المورد") and a.retenues_total:
        _draw(c, 210, 436, _fmt(a.retenue_base_total or a.retenues_total), 8)
        _draw(c, 38, 436, _fmt(a.retenues_total), 8)
    elif not boxes.get("خصم_من_المورد"):
        _mark_x(c, 50, 436)

    c.save()
    return buf.getvalue()


def _page4_tfp_foprolos_overlay(filled: FilledForm) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    a = filled.amounts
    boxes = filled.checkboxes

    if boxes.get("الأداء_على_التكوين_المهني") and a.tfp_amount:
        y = 516 if (a.tfp_rate or 0) <= 0.015 else 500
        _draw(c, 230, y, _fmt(a.tfp_base), 8)
        _draw(c, 112, y, _fmt(a.tfp_amount), 8)
    else:
        _mark_x(c, 120, 500)

    if boxes.get("صندوق_النهوض_بالمسكن") and a.foprolos_amount:
        _draw(c, 270, 210, _fmt(a.foprolos_base), 8)
        _draw(c, 48, 210, _fmt(a.foprolos_amount), 8)
    else:
        _mark_x(c, 55, 210)

    c.save()
    return buf.getvalue()


def _page5_tva_overlay(filled: FilledForm) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    a = filled.amounts
    boxes = filled.checkboxes

    if not boxes.get("الأداء_على_القيمة_المضافة"):
        _mark_x(c, 130, 538)
        c.save()
        return buf.getvalue()

    if a.ca_ht_7:
        _draw(c, 255, 563, _fmt(a.ca_ht_7), 8)
        _draw(c, 125, 563, _fmt(a.ca_ht_7 * 0.07), 8)
    if a.ca_ht_13:
        _draw(c, 255, 550, _fmt(a.ca_ht_13), 8)
        _draw(c, 125, 550, _fmt(a.ca_ht_13 * 0.13), 8)
    if a.ca_ht_19 or a.tva_collectee_19:
        _draw(c, 255, 537, _fmt(a.ca_ht_19 or a.ca_ht), 8)
        _draw(c, 125, 537, _fmt(a.tva_collectee_19 or a.tva_collectee), 8)

    if a.tva_collectee:
        _draw(c, 125, 470, _fmt(a.tva_collectee), 8)
    if a.tva_deductible:
        _draw(c, 125, 455, _fmt(a.tva_deductible), 8)
    if a.tva_nette:
        _draw(c, 45, 440, _fmt(a.tva_nette), 9)
    if a.tva_credit_report:
        _draw(c, 45, 425, _fmt(a.tva_credit_report), 8)
    if a.tva_credit_next:
        _draw(c, 45, 410, _fmt(a.tva_credit_next), 8)

    c.save()
    return buf.getvalue()


def _page8_local_overlay(filled: FilledForm) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    a = filled.amounts
    boxes = filled.checkboxes

    if a.stamp_duty_count or a.stamp_duty_total:
        _draw(c, 270, 627, str(int(a.stamp_duty_count or 0)), 9)
        _draw(c, 50, 627, _fmt(a.stamp_duty_total), 9)

    if boxes.get("المعلوم_على_النزل") and a.hotel_tax_amount:
        _draw(c, 270, 400, _fmt(a.hotel_tax_base), 8)
        _draw(c, 180, 400, f"{(a.hotel_tax_rate or 0) * 100:.0f}%", 8)
        _draw(c, 55, 400, _fmt(a.hotel_tax_amount), 8)
    else:
        _mark_x(c, 60, 400)

    if boxes.get("المعلوم_على_المؤسسات") and a.etablissement_tax_amount:
        _draw(c, 270, 340, _fmt(a.etablissement_tax_base), 8)
        _draw(c, 55, 340, _fmt(a.etablissement_tax_amount), 8)
    else:
        _mark_x(c, 60, 340)

    c.save()
    return buf.getvalue()


def _merge_overlay(base_page, overlay_bytes: bytes):
    overlay = PdfReader(BytesIO(overlay_bytes)).pages[0]
    base_page.merge_page(overlay)
    return base_page


def _resolve_template() -> Path:
    if TEMPLATE.exists():
        return TEMPLATE
    for path in _TEMPLATE_FALLBACKS:
        if path.exists():
            return path
    raise FileNotFoundError(f"Template manquant: {TEMPLATE}")


def fill_official_pdf(filled: FilledForm, out_path: Path) -> Path:
    template = _resolve_template()
    reader = PdfReader(str(template))
    writer = PdfWriter()

    overlays = {
        0: _page1_overlay(filled),
        3: _page4_tfp_foprolos_overlay(filled),
        4: _page5_tva_overlay(filled),
        7: _page8_local_overlay(filled),
    }

    for i, page in enumerate(reader.pages):
        ov = overlays.get(i)
        if ov:
            _merge_overlay(page, ov)
        writer.add_page(page)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("wb") as f:
        writer.write(f)
    return out_path
