"""Recherche dans le guide (FTS5) et validation des champs extraits.

`search_chunks`     : retrouve les passages du guide (RAG pour l'assistant).
`validate_extraction`: confronte un dict extrait d'une photo au REGISTRE DES CHAMPS
                       connu → normalise, signale les champs inconnus et les erreurs.
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from typing import Any

from app.knowledge import db

_WORD = re.compile(r"[\w\u0600-\u06FF]+", re.UNICODE)
_NUM_CLEAN = re.compile(r"[^\d,.\-]")


def _norm(text: Any) -> str:
    """Normalise une étiquette : sans accent, minuscule, ponctuation réduite."""
    s = unicodedata.normalize("NFKD", str(text))
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9\u0600-\u06FF]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------------------
# Recherche plein-texte
# ---------------------------------------------------------------------------
def _fts_query(query: str) -> str | None:
    terms = [t for t in _WORD.findall((query or "").lower()) if len(t) >= 3]
    if not terms:
        return None
    return " OR ".join(f'"{t}"' for t in terms[:12])


def search_chunks(query: str, limit: int = 4) -> list[dict[str, Any]]:
    """Top passages du guide, classés par pertinence (bm25)."""
    if not query or not query.strip():
        return []
    match = _fts_query(query)
    results: list[dict[str, Any]] = []
    try:
        with db.connect() as conn:
            if match:
                rows = conn.execute(
                    """
                    SELECT c.id, c.text, s.number AS section, s.title, bm25(kb_chunks_fts) AS rank
                    FROM kb_chunks_fts
                    JOIN kb_chunks c ON c.id = kb_chunks_fts.rowid
                    LEFT JOIN kb_sections s ON s.id = c.section_id
                    WHERE kb_chunks_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                    """,
                    (match, limit),
                ).fetchall()
                results = [
                    {"id": r["id"], "section": r["section"], "title": r["title"], "text": r["text"]}
                    for r in rows
                ]
            if not results:
                # repli : recherche par sous-chaîne
                like = f"%{query.strip()}%"
                rows = conn.execute(
                    """
                    SELECT c.id, c.text, s.number AS section, s.title
                    FROM kb_chunks c
                    LEFT JOIN kb_sections s ON s.id = c.section_id
                    WHERE c.text LIKE ?
                    LIMIT ?
                    """,
                    (like, limit),
                ).fetchall()
                results = [
                    {"id": r["id"], "section": r["section"], "title": r["title"], "text": r["text"]}
                    for r in rows
                ]
    except sqlite3.Error:
        return []
    return results


# ---------------------------------------------------------------------------
# Référentiel
# ---------------------------------------------------------------------------
def _all(table: str, order: str = "id") -> list[dict[str, Any]]:
    try:
        with db.connect() as conn:
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY {order}").fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []


def vat_rates() -> list[dict[str, Any]]:
    return _all("vat_rates", "rate")


def taxes() -> list[dict[str, Any]]:
    return _all("taxes", "id")


def withholding_lines() -> list[dict[str, Any]]:
    return _all("withholding_lines", "line_no")


def required_documents() -> list[dict[str, Any]]:
    return _all("required_documents", "id")


def known_fields(doc_type: str) -> list[dict[str, Any]]:
    try:
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM declaration_fields WHERE doc_type = ? ORDER BY id", (doc_type,)
            ).fetchall()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []


def all_doc_types() -> list[str]:
    try:
        with db.connect() as conn:
            rows = conn.execute("SELECT DISTINCT doc_type FROM declaration_fields ORDER BY doc_type").fetchall()
        return [r[0] for r in rows]
    except sqlite3.Error:
        return []


# ---------------------------------------------------------------------------
# Validation / normalisation
# ---------------------------------------------------------------------------
_TRUE = {"oui", "yes", "true", "vrai", "1", "نعم", "خاضع"}
_FALSE = {"non", "no", "false", "faux", "0", "لا", "غير خاضع", "معفي"}


def _to_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    cleaned = _NUM_CLEAN.sub("", value).strip()
    if not cleaned or cleaned in {"-", ".", ","}:
        return None
    # 1 234,56 (fr) → 1234.56 ; 1,234.56 (en) → 1234.56
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    else:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        v = value.strip().lower()
        if v in _TRUE:
            return True
        if v in _FALSE:
            return False
    return None


def validate_extraction(doc_type: str, values: dict[str, Any]) -> dict[str, Any]:
    """Mappe/normalise/valide les champs extraits d'une photo pour un type de document.

    Retourne :
      normalized   : {field_key: valeur propre} (uniquement champs connus + valides)
      unknown      : clés extraites non reconnues (à examiner)
      errors       : [{field, value, reason}] valeur invalide
      missing      : champs requis absents
      known        : nombre de champs connus pour ce doc_type
    """
    specs = {f["field_key"]: f for f in known_fields(doc_type)}
    alias_map = _alias_map(doc_type)

    def resolve(raw_key: Any) -> str | None:
        if raw_key in specs:
            return raw_key
        n = _norm(raw_key)
        if not n:
            return None
        if n in alias_map:
            return alias_map[n]
        # tolérance : alias contenu dans l'étiquette (ou l'inverse)
        for alias, key in alias_map.items():
            if alias and (alias in n or n in alias):
                return key
        return None

    normalized: dict[str, Any] = {}
    unknown: list[str] = []
    # champs inconnus = clés reconnues nulle part
    for raw_key, raw_value in (values or {}).items():
        key = resolve(raw_key)
        if not key:
            unknown.append(raw_key)
            continue
        spec = specs[key]
        value, reason = _coerce(raw_value, spec)
        if reason:
            continue  # erreur enregistrée plus bas
        if value is not None:
            normalized[key] = value

    errors: list[dict[str, Any]] = []
    # re-parcours pour collecter les erreurs
    for raw_key, raw_value in (values or {}).items():
        key = resolve(raw_key)
        if not key:
            continue
        _, reason = _coerce(raw_value, specs[key])
        if reason:
            errors.append({"field": key, "value": raw_value, "reason": reason})

    missing = [
        k
        for k, spec in specs.items()
        if spec.get("required") and k not in normalized
    ]

    return {
        "doc_type": doc_type,
        "normalized": normalized,
        "unknown": unknown,
        "errors": errors,
        "missing": missing,
        "known_fields": len(specs),
    }


def _alias_map(doc_type: str) -> dict[str, str]:
    try:
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT alias, field_key FROM field_aliases WHERE doc_type = ?", (doc_type,)
            ).fetchall()
        return {_norm(r["alias"]): r["field_key"] for r in rows if _norm(r["alias"])}
    except sqlite3.Error:
        return {}


def _enum_values(spec: dict[str, Any]) -> list[Any]:
    try:
        return json.loads(spec.get("enum_values") or "[]")
    except json.JSONDecodeError:
        return []


def _coerce(value: Any, spec: dict[str, Any]) -> tuple[Any, str | None]:
    """Retourne (valeur_normalisée, raison_d_erreur|None)."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return None, None
    vtype = spec.get("value_type")

    if vtype == "number":
        num = _to_number(value)
        if num is None:
            return None, "valeur numérique attendue"
        allowed = _enum_values(spec)
        if allowed:
            try:
                if not any(abs(num - float(a)) < 1e-6 for a in allowed):
                    return None, f"valeur hors liste {allowed}"
            except (TypeError, ValueError):
                pass
        return num, None

    if vtype == "boolean":
        b = _to_bool(value)
        if b is None:
            return None, "valeur oui/non attendue"
        return b, None

    if vtype == "enum":
        allowed = _enum_values(spec)
        text = str(value).strip()
        for opt in allowed:
            if str(opt).lower() == text.lower():
                return opt, None
        # forme juridique : tolère « SARL — … » ou préfixe code
        for opt in allowed:
            if text.upper().startswith(str(opt).upper()):
                return opt, None
        return None, f"valeur hors liste {allowed}"

    # text / date
    text = str(value).strip()
    rx = spec.get("regex")
    if rx and not re.match(rx, text):
        return None, "format invalide"
    return text, None
