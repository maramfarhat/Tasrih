"""Génère le PDF « Retenue à la source » — جدول الخصم من المورد.

Reprend la présentation du formulaire officiel `mens_mnt_retenue_ar_0.pdf` :
en-tête Ministère des Finances, identification du déclarant, puis un tableau
RTL d'une ligne par opération de retenue (bénéficiaire, identifiant, nature,
base, taux, montant retenu) et les totaux.

Utilisé par `POST /export/retenue` (comme l'export de la déclaration mensuelle).
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.declaration.models import RetenueDeclaration, RetenueOperation

PAGE_W, PAGE_H = A4  # 595 x 842
MARGIN = 36
ROW_H = 16.0

_LATIN_PATHS = [
    Path("/usr/share/fonts/TTF/DejaVuSans.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
]
_ARABIC_PATHS = [
    Path("/usr/share/fonts/noto/NotoNaskhArabic-Regular.ttf"),
    Path("/usr/share/fonts/noto/NotoSansArabic-Regular.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
]

_latin = "Helvetica"
_arabic = "Helvetica"


def _register() -> None:
    global _latin, _arabic
    if _latin == "Helvetica":
        for p in _LATIN_PATHS:
            if p.exists():
                try:
                    pdfmetrics.registerFont(TTFont("RetLatin", str(p)))
                    _latin = "RetLatin"
                    break
                except Exception:
                    continue
    if _arabic == "Helvetica":
        for p in _ARABIC_PATHS:
            if p.exists():
                try:
                    pdfmetrics.registerFont(TTFont("RetArabic", str(p)))
                    _arabic = "RetArabic"
                    break
                except Exception:
                    continue


def _ar(text: str | None) -> str:
    """Arabic shaping + bidi (ou fallback ASCII)."""
    if not text:
        return ""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(str(text)))
    except Exception:
        return str(text)


def _draw_ar(c: canvas.Canvas, x: float, y: float, text: str, size: float = 9, align: str = "right") -> None:
    s = _ar(text)
    c.setFont(_arabic, size)
    try:
        if align == "right":
            c.drawRightString(x, y, s)
        elif align == "center":
            c.drawCentredString(x, y, s)
        else:
            c.drawString(x, y, s)
    except Exception:
        c.setFont("Helvetica", size)
        ascii_s = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in str(text))
        c.drawString(x, y, ascii_s)


def _draw_lat(c: canvas.Canvas, x: float, y: float, text: str, size: float = 8, align: str = "left") -> None:
    c.setFont(_latin, size)
    s = str(text or "")
    try:
        if align == "right":
            c.drawRightString(x, y, s)
        elif align == "center":
            c.drawCentredString(x, y, s)
        else:
            c.drawString(x, y, s)
    except Exception:
        c.setFont("Helvetica", size)
        c.drawString(x, y, "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in s))


def _has_arabic(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06ff" for ch in (text or ""))


def _draw_name(c: canvas.Canvas, x: float, y: float, text: str, size: float = 7.5) -> None:
    """Nom de bénéficiaire : font arabe si caractères arabes, sinon font latine."""
    if not text:
        return
    if _has_arabic(text):
        _draw_ar(c, x, y, text, size, align="right")
    else:
        _draw_lat(c, x, y, text, size, align="right")


def _money(v: float | None) -> str:
    if v is None:
        return ""
    return f"{v:,.3f}".replace(",", " ")


# Colonnes du tableau, de droite à gauche : (titre_ar, largeur)
_COLUMNS: list[tuple[str, float]] = [
    ("ر.ت", 26),
    ("الاسم واللقب أو الاسم الاجتماعي", 148),
    ("المعرف الجبائي", 84),
    ("رمز الصنف", 92),
    ("المبلغ الخام", 68),
    ("نسبة الخصم", 45),
    ("مبلغ الخصم من المورد", 60),
]

_TOTAL_W = sum(w for _, w in _COLUMNS)
_X_RIGHT = PAGE_W - MARGIN


def _column_edges() -> list[float]:
    """Bords des colonnes de droite à gauche (x décroissant)."""
    edges = [_X_RIGHT]
    for _, w in _COLUMNS:
        edges.append(edges[-1] - w)
    return edges


def _header(c: canvas.Canvas, decl: RetenueDeclaration) -> float:
    y = PAGE_H - MARGIN
    _draw_ar(c, _X_RIGHT, y, "الجمهورية التونسية", 11)
    _draw_ar(c, _X_RIGHT, y - 14, "وزارة المالية", 10)
    _draw_ar(c, _X_RIGHT, y - 28, "الإدارة العامة للأداءات", 9)
    _draw_lat(c, MARGIN, y, "République Tunisienne", 8)
    _draw_lat(c, MARGIN, y - 12, "Ministère des Finances", 8)
    _draw_lat(c, MARGIN, y - 24, "Direction Générale des Impôts", 7)

    title_y = y - 58
    _draw_ar(
        c,
        PAGE_W / 2,
        title_y,
        "جدول الخصم من المورد بعنوان المبالغ المدفوعة لحساب الغير",
        12,
        align="center",
    )
    _draw_lat(
        c,
        PAGE_W / 2,
        title_y - 13,
        "Tableau des retenues à la source (montants payés pour le compte de tiers)",
        7.5,
        align="center",
    )

    c.setStrokeColorRGB(0, 31 / 255, 92 / 255)
    c.setLineWidth(1)
    c.line(MARGIN, title_y - 22, PAGE_W - MARGIN, title_y - 22)

    info_y = title_y - 40
    _draw_ar(c, _X_RIGHT, info_y, f"المعرف الجبائي : {decl.declarant_id or '—'}", 9)
    period = f"{decl.month:02d}/{decl.year}" if decl.month and decl.year else "—"
    _draw_ar(c, PAGE_W / 2, info_y, f"الفترة : {period}", 9, align="center")
    acte = {"0": "تصريح أولي", "1": "تصريح تداركي", "2": "تصريح تصحيحي"}.get(
        str(decl.acte_depot), f"نوع التصريح : {decl.acte_depot or '—'}"
    )
    _draw_ar(c, MARGIN, info_y, acte, 9, align="left")
    return info_y - 16


def _table_head(c: canvas.Canvas, y: float) -> float:
    edges = _column_edges()
    head_h = 32
    c.setFillColorRGB(0.94, 0.96, 0.99)
    c.rect(MARGIN, y - head_h, _TOTAL_W, head_h, stroke=0, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.setStrokeColorRGB(0.72, 0.76, 0.82)
    c.setLineWidth(0.6)
    c.rect(MARGIN, y - head_h, _TOTAL_W, head_h, stroke=1, fill=0)
    for x in edges[1:-1]:
        c.line(x, y, x, y - head_h)
    # titres (2 lignes max, centrés)
    for i, (title, width) in enumerate(_COLUMNS):
        cx = (edges[i] + edges[i + 1]) / 2
        words = title.split()
        lines = []
        cur = ""
        for w in words:
            trial = (cur + " " + w).strip()
            if pdfmetrics.stringWidth(_ar(trial), _arabic, 7) <= width - 4 or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        for j, line in enumerate(lines[:2]):
            _draw_ar(c, cx, y - 12 - j * 10, line, 7, align="center")
    return y - head_h


def _row(c: canvas.Canvas, y: float, idx: int, cert, op) -> float:
    edges = _column_edges()
    c.setStrokeColorRGB(0.82, 0.85, 0.89)
    c.setLineWidth(0.5)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    for x in edges[1:-1]:
        c.line(x, y, x, y - ROW_H)

    values = [
        (str(idx), "center"),
        (cert.beneficiary_name or "", "right"),
        (cert.beneficiary_id or "", "center"),
        (op.nature or op.id_type_operation or "", "center"),
        (_money(op.montant_ht), "center"),
        (f"{op.taux_rs:.2f}%" if op.taux_rs is not None else "", "center"),
        (_money(op.montant_rs), "center"),
    ]
    ty = y - 11
    for i, (val, align) in enumerate(values):
        cx = (edges[i] + edges[i + 1]) / 2
        if i == 1:
            _draw_name(c, edges[i] - 4, ty, val, 7.5)
        elif i == 0:
            _draw_lat(c, cx, ty, val, 7.5, align="center")
        else:
            _draw_lat(c, cx, ty, val, 7.5, align="center")
    return y - ROW_H


def _totals(c: canvas.Canvas, y: float, decl: RetenueDeclaration, n_rows: int) -> float:
    edges = _column_edges()
    c.setStrokeColorRGB(0, 31 / 255, 92 / 255)
    c.setLineWidth(1)
    c.line(MARGIN, y, PAGE_W - MARGIN, y)
    ty = y - 12
    _draw_ar(c, edges[1] - 4, ty, "المجموع", 8, align="right")
    _draw_lat(c, (edges[4] + edges[5]) / 2, ty, _money(decl.total_ht), 8, align="center")
    _draw_lat(c, (edges[6] + edges[7]) / 2, ty, _money(decl.total_rs), 8, align="center")
    _draw_lat(
        c,
        MARGIN,
        y - 30,
        f"Nombre d'opérations : {n_rows}  ·  Total retenue : {_money(decl.total_rs)} TND",
        7,
    )
    return y - 40


def export_retenue_pdf(decl: RetenueDeclaration, out_path: Path) -> Path:
    """Écrit le PDF « Retenue à la source » et retourne le chemin."""
    _register()
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle("Retenue à la source")

    y = _header(c, decl)
    y = _table_head(c, y)

    rows = [
        (cert, op)
        for cert in decl.certificates
        for op in (cert.operations or [None])
    ]

    for i, (cert, op) in enumerate(rows, start=1):
        if y - ROW_H < MARGIN + 60:
            c.showPage()
            _register()
            y = PAGE_H - MARGIN - 20
            y = _table_head(c, y)
        y = _row(c, y, i, cert, op or RetenueOperation())

    y = _totals(c, y, decl, len(rows))

    c.setFont("Helvetica", 6.5)
    c.setFillColorRGB(0.42, 0.45, 0.5)
    c.drawString(MARGIN, MARGIN + 20, "Document généré par Tasrih — à vérifier avant dépôt.")
    c.drawRightString(PAGE_W - MARGIN, MARGIN + 20, "TEJ — tej.finances.gov.tn")

    c.save()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(buf.getvalue())
    return out_path
