"""Ingestion du guide officiel dans la base de connaissances.

- Extrait le texte (pdftotext si dispo, sinon pypdf).
- Découpe en sections (0..10) puis en chunks indexés en FTS5.
- Charge le référentiel fiscal et le registre des champs (seed.py).

Idempotent : ré-ingérer remplace l'ancien document.

Usage :
    PYTHONPATH=backend backend/.venv/bin/python -m app.knowledge.ingest
    PYTHONPATH=backend backend/.venv/bin/python -m app.knowledge.ingest chemin/vers/guide.pdf
"""

from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

from app.config import DATA
from app.knowledge import db, seed

DEFAULT_PDF = DATA / "knowledge" / "guide-declaration-mensuelle-tunisie.pdf"
SLUG = "guide-declaration-mensuelle-tunisie"
TITLE = "Guide technique — Déclaration mensuelle des impôts et taxes (Tunisie)"

HEADING = re.compile(r"^\s*(\d{1,2})\.\s+([A-ZÀ-ÖØ-Þ][^\n]{3,})$")
CHUNK_SIZE = 700


# ---------------------------------------------------------------------------
# Extraction du texte
# ---------------------------------------------------------------------------
def _normalize_wordwrap(text: str) -> str:
    """pypdf (rendu Google Docs) met un mot par ligne : on recolle les paragraphes."""
    out: list[str] = []
    buf: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if buf:
                out.append(" ".join(buf))
                buf = []
            continue
        buf.append(line)
    if buf:
        out.append(" ".join(buf))
    return "\n".join(out)


def extract_pages(path: Path) -> list[tuple[int, str]]:
    """Retourne [(numéro_page, texte)] — layout préservé si pdftotext est présent."""
    if shutil.which("pdftotext"):
        proc = subprocess.run(
            ["pdftotext", "-layout", str(path), "-"],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            pages = proc.stdout.split("\f")
            return [(i + 1, p) for i, p in enumerate(pages) if p.strip()]

    # Repli : pypdf sans dépendance système
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[tuple[int, str]] = []
    for i, page in enumerate(reader.pages):
        text = _normalize_wordwrap(page.extract_text() or "")
        if text.strip():
            pages.append((i + 1, text))
    return pages


# ---------------------------------------------------------------------------
# Découpage
# ---------------------------------------------------------------------------
def split_sections(pages: list[tuple[int, str]]) -> list[dict]:
    sections: list[dict] = []
    current = {"number": "pre", "title": "Introduction", "page": pages[0][0] if pages else 1, "lines": []}
    for page_no, text in pages:
        for line in text.splitlines():
            m = HEADING.match(line)
            if m:
                if current["lines"]:
                    sections.append(current)
                current = {"number": m.group(1), "title": m.group(2).strip(), "page": page_no, "lines": []}
            else:
                current["lines"].append(line)
    if current["lines"]:
        sections.append(current)
    return sections


def chunk_text(lines: list[str], size: int = CHUNK_SIZE) -> list[str]:
    chunks: list[str] = []
    buf: list[str] = []
    length = 0
    for line in lines:
        s = line.rstrip()
        if not s.strip():
            continue
        buf.append(s)
        length += len(s) + 1
        if length >= size:
            chunks.append("\n".join(buf))
            # recouvrement : on garde la dernière ligne
            buf = buf[-1:]
            length = sum(len(x) + 1 for x in buf)
    if buf:
        chunks.append("\n".join(buf))
    return [c for c in chunks if c.strip()]


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------
def ingest(pdf_path: Path | None = None) -> dict:
    db.init_db()
    pdf_path = pdf_path or DEFAULT_PDF
    if not pdf_path.exists():
        raise FileNotFoundError(f"Guide introuvable : {pdf_path}")

    pages = extract_pages(pdf_path)
    full_text = "\n".join(t for _, t in pages)
    text_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()
    sections = split_sections(pages)

    with db.connect() as conn:
        # remplace l'ancien document (cascade sections + chunks, triggers FTS)
        old = conn.execute("SELECT id FROM kb_documents WHERE slug = ?", (SLUG,)).fetchone()
        if old:
            conn.execute("DELETE FROM kb_documents WHERE id = ?", (old["id"],))
        cur = conn.execute(
            "INSERT INTO kb_documents (slug, title, source_path, page_count, text_hash, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (SLUG, TITLE, str(pdf_path), len(pages), text_hash, db._utcnow()),
        )
        doc_id = int(cur.lastrowid)

        chunk_count = 0
        for ordinal, section in enumerate(sections):
            srow = conn.execute(
                "INSERT INTO kb_sections (document_id, number, title, ordinal, page) VALUES (?, ?, ?, ?, ?)",
                (doc_id, section["number"], section["title"], ordinal, section["page"]),
            )
            section_id = int(srow.lastrowid)
            for chunk in chunk_text(section["lines"]):
                conn.execute(
                    "INSERT INTO kb_chunks (document_id, section_id, ordinal, text) VALUES (?, ?, ?, ?)",
                    (doc_id, section_id, chunk_count, chunk),
                )
                chunk_count += 1

    _load_reference()
    return {"document": SLUG, "pages": len(pages), "sections": len(sections), "chunks": chunk_count, **db.stats()}


def _load_reference() -> None:
    """Charge/rafraîchit le référentiel fiscal + le registre de champs."""
    with db.connect() as conn:
        # tables de référence : on remplace tout (petites et versionnées dans le code)
        conn.execute("DELETE FROM vat_rates")
        conn.execute("DELETE FROM withholding_lines")
        conn.execute("DELETE FROM taxes")
        conn.execute("DELETE FROM required_documents")
        conn.execute("DELETE FROM field_aliases")

        conn.executemany(
            "INSERT INTO vat_rates (rate, label, category, notes) VALUES (?, ?, ?, ?)",
            seed.VAT_RATES,
        )
        conn.executemany(
            "INSERT INTO withholding_lines (line_no, nature, base, rate, reference, pieces, source) "
            "VALUES (:line_no, :nature, :base, :rate, :reference, :pieces, :source)",
            [{**row, "source": seed.SOURCE} for row in seed.WITHHOLDING_LINES],
        )
        conn.executemany(
            "INSERT INTO taxes (code, name_fr, name_ar, section, base, rate, rate_value, rate_unit, conditions, pieces, source) "
            "VALUES (:code, :name_fr, :name_ar, :section, :base, :rate, :rate_value, :rate_unit, :conditions, :pieces, :source)",
            [
                {"name_ar": None, "conditions": "", "pieces": "", **row, "source": seed.SOURCE}
                for row in seed.TAXES
            ],
        )
        conn.executemany(
            "INSERT INTO required_documents (category, item, notes) VALUES (?, ?, ?)",
            seed.REQUIRED_DOCUMENTS,
        )

        # registre des champs + alias (conservés entre ingés)
        for field in seed.DECLARATION_FIELDS:
            conn.execute(
                """
                INSERT INTO declaration_fields
                    (doc_type, field_key, label_fr, label_ar, value_type, required, enum_values, regex, model_path, description)
                VALUES (:doc_type, :field_key, :label_fr, :label_ar, :value_type, :required, :enum_values, :regex, :model_path, :description)
                ON CONFLICT(doc_type, field_key) DO UPDATE SET
                    label_fr = excluded.label_fr, label_ar = excluded.label_ar,
                    value_type = excluded.value_type, required = excluded.required,
                    enum_values = excluded.enum_values, regex = excluded.regex,
                    model_path = excluded.model_path, description = excluded.description
                """,
                field,
            )
        for doc_type, field_key, alias in seed.ALIASES:
            conn.execute(
                "INSERT OR IGNORE INTO field_aliases (doc_type, field_key, alias) VALUES (?, ?, ?)",
                (doc_type, field_key, alias.lower().strip()),
            )


def main() -> None:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    result = ingest(target)
    print("Ingestion terminée :")
    for key, value in result.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
