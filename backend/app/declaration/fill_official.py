"""Remplit le PDF officiel mensuelle2026.pdf (12 pages) par overlay."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.config import BACKEND
from app.declaration.models import FilledForm

TEMPLATE = BACKEND / "data" / "templates" / "mensuelle2026.pdf"
FONT_PATHS = [
    Path(r"C:\Windows\Fonts\arial.ttf"),
    Path(r"C:\Windows\Fonts\tahoma.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
]

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

        reshaped = arabic_reshaper.reshape(str(text))
        return get_display(reshaped)
    except Exception:
        return str(text)


def _safe_draw_text(text: str, rtl: bool = False) -> str:
    raw = str(text or "")
    if not raw:
        return ""
    s = _arab(raw) if rtl else raw
    try:
        s.encode("latin-1")
        return s[:90]
    except UnicodeEncodeError:
        return "".join(ch if ord(ch) < 256 else "?" for ch in raw)[:90]


def _draw(c: canvas.Canvas, x: float, y: float, text: str, size: float = 9, rtl: bool = False) -> None:
    if text is None or text == "":
        return
    font = _ensure_font()
    c.setFont(font, size)
    s = _safe_draw_text(str(text), rtl=rtl and font != "Helvetica")
    if font == "Helvetica":
        s = _safe_draw_text(str(text), rtl=False)
    try:
        c.drawString(x, y, s[:90])
    except Exception:
        c.setFont("Helvetica", size)
        ascii_s = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in str(text))[:90]
        c.drawString(x, y, ascii_s)


def _draw_boxes(c: canvas.Canvas, x: float, y: float, text: str, spacing: float = 13, size: float = 10) -> None:
    """Draw characters into consecutive form boxes."""
    font = _ensure_font()
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
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, "X")


def _clean_address(address: str) -> tuple[str, str]:
    """Return (address_without_postal, postal_code)."""
    raw = re.sub(r"\s+", " ", (address or "").strip())
    raw = re.sub(r"\bsign\b", "", raw, flags=re.I).strip(" ,+")
    postal = ""
    m = re.search(r"\b(\d{4})\b", raw)
    if m:
        postal = m.group(1)
        # drop trailing postal from address line if present
        raw = re.sub(rf"\b{postal}\b", "", raw).strip(" ,+")
    return raw, postal


def _page1_overlay(filled: FilledForm) -> bytes:
    """
    Coordonnées calibrées sur mensuelle2026.pdf (A4, origin bas-gauche).
    Année / mois / code · matricule · nom · adresse · CP · activité · cases.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    p = filled.profile
    m = filled.month
    boxes = filled.checkboxes

    # —— En-tête: السنة / الشهر / رمز التصريح (cases individuelles)
    _draw_boxes(c, 125, 724, f"{m.year:04d}", spacing=14.5, size=11)
    _draw_boxes(c, 238, 724, f"{m.month:02d}", spacing=14.5, size=11)
    _draw_boxes(c, 325, 724, str(m.declaration_code.value), spacing=14.5, size=11)

    # —— المعرف الجبائي (ligne de cases sous l'en-tête)
    tax_bits = [
        (p.tax_id or "").replace(" ", ""),
        (p.vat_code or "").strip(),
        (p.category_code or "").strip(),
        (p.secondary_establishment or "").strip(),
    ]
    tax_line = " ".join(b for b in tax_bits if b)
    if tax_line:
        _draw(c, 165, 698, tax_line[:42], 9)

    # —— Identité (lignes pointillées)
    name = (p.name or "")[:55]
    addr, postal = _clean_address(p.address or "")
    if not postal and p.postal_code:
        postal = re.sub(r"\D", "", p.postal_code)[:4]
    # drop leading establishment noise like "000 "
    addr = re.sub(r"^0{2,3}\s*", "", addr).strip(" ,+")
    addr = addr[:60]
    activity = (p.activity or "")[:50]

    _draw(c, 40, 658, name, 9)
    _draw(c, 40, 641, addr, 8)
    if postal:
        _draw_boxes(c, 108, 622, postal[:4], spacing=14, size=10)
    _draw(c, 40, 611, activity, 9)

    # —— Cases type d'impôt (ligne horizontale)
    _mark(c, 518, 546, boxes.get("خصم_من_المورد", False))
    _mark(c, 462, 546, boxes.get("الأداء_على_التكوين_المهني", False))
    _mark(c, 400, 546, boxes.get("صندوق_النهوض_بالمسكن", False))
    _mark(c, 338, 546, boxes.get("المعلوم_على_الاستهلاك", False))
    _mark(c, 282, 546, boxes.get("الأداء_على_القيمة_المضافة", False))
    _mark(c, 228, 546, boxes.get("معاليم_أخرى_على_رقم_المعاملات", False))
    _mark(c, 172, 546, boxes.get("معلوم_الطابع_الجبائي", False))
    _mark(c, 118, 541, boxes.get("المعلوم_على_المؤسسات", False))
    _mark(c, 74, 541, boxes.get("المعلوم_على_النزل", False))
    _mark(c, 40, 541, boxes.get("معلوم_الإجازة", False))

    c.save()
    return buf.getvalue()


def _page5_tva_overlay(filled: FilledForm) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    a = filled.amounts
    if a.ca_ht_19:
        _draw(c, 270, 536, f"{a.ca_ht_19:.3f}", 9)
    if a.tva_collectee_19:
        _draw(c, 135, 536, f"{a.tva_collectee_19:.3f}", 9)
    if a.ca_ht_13:
        _draw(c, 270, 549, f"{a.ca_ht_13:.3f}", 9)
    if a.ca_ht_7:
        _draw(c, 270, 561, f"{a.ca_ht_7:.3f}", 9)
    if a.tva_nette:
        _draw(c, 55, 470, f"{a.tva_nette:.3f}", 9)
    if a.tva_collectee:
        _draw(c, 135, 500, f"{a.tva_collectee:.3f}", 9)
    if a.tva_deductible:
        _draw(c, 135, 485, f"{a.tva_deductible:.3f}", 9)
    c.save()
    return buf.getvalue()


def _page8_local_overlay(filled: FilledForm) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    a = filled.amounts
    boxes = filled.checkboxes
    if a.stamp_duty_total:
        _draw(c, 40, 780, f"{a.stamp_duty_total:.3f}", 9)
    if boxes.get("المعلوم_على_النزل") and a.hotel_tax_base:
        _draw(c, 280, 430, f"{a.hotel_tax_base:.3f}", 9)
        _draw(c, 80, 430, f"{a.hotel_tax_amount:.3f}", 9)
    if boxes.get("المعلوم_على_المؤسسات") and a.etablissement_tax_base:
        _draw(c, 280, 390, f"{a.etablissement_tax_base:.3f}", 9)
        _draw(c, 80, 390, f"{a.etablissement_tax_amount:.3f}", 9)
    c.save()
    return buf.getvalue()


def _merge_overlay(base_page, overlay_bytes: bytes):
    overlay = PdfReader(BytesIO(overlay_bytes)).pages[0]
    base_page.merge_page(overlay)
    return base_page


def fill_official_pdf(filled: FilledForm, out_path: Path) -> Path:
    if not TEMPLATE.exists():
        raise FileNotFoundError(f"Template manquant: {TEMPLATE}")
    reader = PdfReader(str(TEMPLATE))
    writer = PdfWriter()

    overlays = {
        0: _page1_overlay(filled),
        4: _page5_tva_overlay(filled) if filled.checkboxes.get("الأداء_على_القيمة_المضافة") else None,
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
