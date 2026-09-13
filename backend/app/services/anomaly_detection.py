"""Règles de détection d'anomalies — DGI (administration fiscale).

IMPORTANT : aucune boîte noire, aucun ML. Uniquement des seuils transparents et
explicables. Chaque fonction est **pure** (pas d'accès DB/API) et retourne soit
`None`, soit un dictionnaire :

    {
      "flag_type": "manual_override" | "revenue_mismatch" | "sudden_drop",
      "severity": "low" | "medium" | "high",
      "evidence": {...},          # les chiffres exacts, pour l'inspecteur
      "explanation": "phrase en langage clair",
    }

Les fonctions ne lèvent pas d'exception : les entrées manquantes → `None`.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

Flag = dict[str, Any]

MATERIAL_FIELDS_DEFAULT: tuple[str, ...] = (
    "chiffre_affaires_declare",
    "tva_collectee",
    "tva_deductible",
    "retenue_totale",
)


def _num(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct_change(old: float, new: float) -> float:
    if old == 0:
        return 0.0 if new == 0 else 100.0
    return round((new - old) / abs(old) * 100.0, 2)


def _money(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:,.3f}".replace(",", " ")


def check_manual_override(
    declaration: Mapping[str, Any],
    field_edits: Sequence[Mapping[str, Any]],
    material_fields: Iterable[str] = MATERIAL_FIELDS_DEFAULT,
    tolerance_pct: float = 5,
) -> list[Flag]:
    """Signale toute correction manuelle d'une valeur matérielle issue de l'OCR.

    Ce n'est pas forcément frauduleux : c'est un drapeau de **transparence**.
    On signale chaque écart (hausse ou baisse) au-delà de `tolerance_pct`.

    Evidence : field_name, ocr_value, manual_value, delta_percentage, comment, edited_at.
    Sévérité : low si commentaire + écart modéré ; medium/high si grand écart ou
    commentaire absent (le commentaire est obligatoire côté contribuable).
    """
    flags: list[Flag] = []
    material = set(material_fields)
    for edit in field_edits or []:
        field = str(edit.get("field_name") or "")
        if field not in material:
            continue
        ocr = _num(edit.get("ocr_extracted_value"))
        manual = _num(edit.get("manual_value"))
        if ocr is None or manual is None:
            continue
        delta = _pct_change(ocr, manual)
        if abs(delta) <= tolerance_pct:
            continue
        comment = (edit.get("comment") or "").strip()
        if not comment:
            severity = "high"
        elif abs(delta) > 60:
            severity = "high"
        elif abs(delta) > 30:
            severity = "medium"
        else:
            severity = "low"
        evidence = {
            "field_name": field,
            "ocr_value": ocr,
            "manual_value": manual,
            "delta_percentage": delta,
            "comment": comment or None,
            "comment_missing": not comment,
            "edited_at": edit.get("edited_at"),
        }
        direction = "augmentation" if delta > 0 else "baisse"
        if comment:
            explanation = (
                f"Le contribuable a modifié manuellement « {field} » de "
                f"{_money(ocr)} TND (OCR) à {_money(manual)} TND, soit une {direction} "
                f"de {abs(delta):.1f} %, avec le motif : « {comment} »."
            )
        else:
            explanation = (
                f"Le contribuable a modifié manuellement « {field} » de {_money(ocr)} TND "
                f"(OCR) à {_money(manual)} TND ({direction} de {abs(delta):.1f} %) "
                "sans motif enregistré."
            )
        flags.append(
            {
                "flag_type": "manual_override",
                "severity": severity,
                "evidence": evidence,
                "explanation": explanation,
            }
        )
    return flags


def check_revenue_invoice_mismatch(
    declaration: Mapping[str, Any],
    invoices_summary: Mapping[str, Any] | None,
    threshold_pct: float = 20,
) -> Flag | None:
    """CA déclaré sensiblement inférieur au volume de facturation électronique.

    Si `chiffre_affaires_declare` est plus de `threshold_pct` % **en dessous** du
    total HT facturé (même entreprise / même mois), on lève un drapeau.

    Evidence : declared_amount, invoiced_amount, gap_amount, gap_percentage, invoice_ids.
    """
    if not invoices_summary:
        return None
    declared = _num(declaration.get("chiffre_affaires_declare"))
    invoiced = _num(invoices_summary.get("total_invoice_amount_ht"))
    if declared is None or invoiced is None or invoiced <= 0:
        return None
    gap_amount = round(invoiced - declared, 3)
    gap_pct = round(gap_amount / invoiced * 100.0, 2)
    if gap_pct <= threshold_pct:
        return None
    if gap_pct > 60:
        severity = "high"
    elif gap_pct > 40:
        severity = "medium"
    else:
        severity = "low"
    invoice_ids = invoices_summary.get("invoice_ids") or []
    explanation = (
        f"Chiffre d'affaires déclaré {_money(declared)} TND contre "
        f"{_money(invoiced)} TND de factures électroniques (écart {gap_pct:.1f} %, "
        f"soit {_money(gap_amount)} TND)."
    )
    return {
        "flag_type": "revenue_mismatch",
        "severity": severity,
        "evidence": {
            "declared_amount": declared,
            "invoiced_amount": invoiced,
            "gap_amount": gap_amount,
            "gap_percentage": gap_pct,
            "invoice_ids": list(invoice_ids)[:50],
            "threshold_pct": threshold_pct,
        },
        "explanation": explanation,
    }


def check_sudden_drop(
    business_id: int,
    current_declaration: Mapping[str, Any],
    historical_declarations: Sequence[Mapping[str, Any]],
    drop_threshold_pct: float = 50,
    lookback_months: int = 6,
) -> Flag | None:
    """Baisse brutale par rapport à la moyenne historique (hors effet saisonnier).

    Moyenne du CA déclaré sur les `lookback_months` derniers mois (hors mois courant).
    Si le mois courant est plus de `drop_threshold_pct` % sous cette moyenne ET que
    le même mois de l'année précédente ne présente pas la même baisse → drapeau.

    Evidence : historical_average, current_amount, drop_percentage, months used,
    same-month-last-year si disponible.
    """
    current = _num(current_declaration.get("chiffre_affaires_declare"))
    if current is None:
        return None

    def key(d: Mapping[str, Any]) -> tuple[int, int]:
        return (int(d.get("year") or 0), int(d.get("month") or 0))

    cur_key = key(current_declaration)
    history = [d for d in (historical_declarations or []) if key(d) != cur_key]
    # les plus récents d'abord
    history.sort(key=key, reverse=True)
    window = history[: max(1, lookback_months)]
    amounts = [_num(d.get("chiffre_affaires_declare")) for d in window]
    amounts_ok = [a for a in amounts if a is not None]
    if not amounts_ok:
        return None
    avg = sum(amounts_ok) / len(amounts_ok)
    if avg <= 0:
        return None
    drop = round((avg - current) / avg * 100.0, 2)
    if drop <= drop_threshold_pct:
        return None

    # même mois l'année précédente
    same_month = next(
        (
            d
            for d in historical_declarations or []
            if int(d.get("month") or 0) == cur_key[1]
            and int(d.get("year") or 0) == cur_key[0] - 1
        ),
        None,
    )
    seasonal_ok = True
    same_month_amount = None
    if same_month is not None:
        same_month_amount = _num(same_month.get("chiffre_affaires_declare"))
        prev_avg = sum(
            a
            for a in (
                _num(d.get("chiffre_affaires_declare"))
                for d in history
                if int(d.get("year") or 0) == cur_key[0] - 1
            )
            if a is not None
        )
        if same_month_amount is not None and prev_avg > 0:
            prev_year_decline = (prev_avg - same_month_amount) / prev_avg * 100.0
            # si la même baisse existait déjà l'an dernier → probablement saisonnier
            seasonal_ok = prev_year_decline < drop_threshold_pct
    if not seasonal_ok:
        return None

    severity = "high" if drop >= 70 else "medium"
    explanation = (
        f"Baisse brutale du chiffre d'affaires : {_money(current)} TND ce mois contre "
        f"une moyenne de {_money(avg)} TND sur les {len(amounts_ok)} derniers mois "
        f"({drop:.1f} % de baisse)."
    )
    return {
        "flag_type": "sudden_drop",
        "severity": severity,
        "evidence": {
            "business_id": business_id,
            "current_amount": current,
            "historical_average": round(avg, 3),
            "drop_percentage": drop,
            "months_used": [
                {
                    "year": d.get("year"),
                    "month": d.get("month"),
                    "chiffre_affaires_declare": _num(d.get("chiffre_affaires_declare")),
                }
                for d in window
            ],
            "same_month_last_year": (
                None
                if same_month is None
                else {
                    "year": same_month.get("year"),
                    "month": same_month.get("month"),
                    "chiffre_affaires_declare": same_month_amount,
                }
            ),
            "drop_threshold_pct": drop_threshold_pct,
        },
        "explanation": explanation,
    }


def run_all_rules(
    declaration: Mapping[str, Any],
    field_edits: Sequence[Mapping[str, Any]] | None = None,
    invoices_summary: Mapping[str, Any] | None = None,
    historical_declarations: Sequence[Mapping[str, Any]] | None = None,
) -> list[Flag]:
    """Exécute les trois règles et renvoie la liste des drapeaux levés."""
    flags: list[Flag] = []
    flags.extend(check_manual_override(declaration, field_edits or []))
    mismatch = check_revenue_invoice_mismatch(declaration, invoices_summary)
    if mismatch:
        flags.append(mismatch)
    drop = check_sudden_drop(
        int(declaration.get("business_id") or 0),
        declaration,
        historical_declarations or [],
    )
    if drop:
        flags.append(drop)
    return flags
