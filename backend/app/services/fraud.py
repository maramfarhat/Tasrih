"""Exécution de la détection (relie les règles pures à la base DGI)."""

from __future__ import annotations

from typing import Any

from app import admin_db
from app.services import anomaly_detection


def run_detection_for_declaration(declaration: dict[str, Any]) -> list[dict[str, Any]]:
    """Évalue une déclaration et remplace ses drapeaux **ouverts** (pas les traités)."""
    business_id = int(declaration["business_id"])
    edits = admin_db.list_field_edits(int(declaration["id"]))
    invoices = admin_db.get_invoices_summary(
        business_id, int(declaration["year"]), int(declaration["month"])
    )
    history = admin_db.list_declarations(business_id)
    flags = anomaly_detection.run_all_rules(
        declaration=declaration,
        field_edits=edits,
        invoices_summary=invoices,
        historical_declarations=history,
    )
    admin_db.clear_open_flags_for_declaration(int(declaration["id"]))
    for f in flags:
        admin_db.add_flag(
            business_id=business_id,
            declaration_id=int(declaration["id"]),
            flag_type=f["flag_type"],
            severity=f["severity"],
            evidence=f["evidence"],
            explanation=f["explanation"],
        )
    return flags


def run_detection_all() -> dict[str, Any]:
    """Lance les trois règles sur toutes les déclarations et insère les drapeaux."""
    declarations = admin_db.list_all_declarations()
    total_flags = 0
    per_type: dict[str, int] = {}
    for decl in declarations:
        flags = run_detection_for_declaration(decl)
        total_flags += len(flags)
        for f in flags:
            per_type[f["flag_type"]] = per_type.get(f["flag_type"], 0) + 1
    return {
        "declarations_scanned": len(declarations),
        "flags_created": total_flags,
        "by_type": per_type,
    }
