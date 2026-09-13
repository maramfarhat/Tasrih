"""Tests unitaires des règles de détection (fonctions pures).

Exécution sans pytest :
    cd backend && PYTHONPATH=. .venv/bin/python tests/test_anomaly_detection.py

Exécution avec pytest (si installé) :
    cd backend && PYTHONPATH=. .venv/bin/pytest tests/
"""

from __future__ import annotations

from app.services.anomaly_detection import (
    check_manual_override,
    check_revenue_invoice_mismatch,
    check_sudden_drop,
)


# ——— Rule A : manual_override ———


def test_manual_override_within_tolerance_is_ignored():
    decl = {"id": 1, "chiffre_affaires_declare": 12000}
    edits = [
        {
            "field_name": "chiffre_affaires_declare",
            "ocr_extracted_value": 12000,
            "manual_value": 12300,  # +2.5 % < 5 %
            "comment": "",
        }
    ]
    assert check_manual_override(decl, edits) == []


def test_manual_override_flags_large_change_without_comment_as_high():
    decl = {"id": 1}
    edits = [
        {
            "field_name": "tva_collectee",
            "ocr_extracted_value": 8200,
            "manual_value": 3100,
            "comment": "",
            "edited_at": "2026-09-13T10:00:00Z",
        }
    ]
    flags = check_manual_override(decl, edits)
    assert len(flags) == 1
    f = flags[0]
    assert f["flag_type"] == "manual_override"
    assert f["severity"] == "high"
    assert f["evidence"]["delta_percentage"] == -62.2
    assert f["evidence"]["comment_missing"] is True


def test_manual_override_with_comment_small_delta_is_low():
    decl = {"id": 1}
    edits = [
        {
            "field_name": "tva_deductible",
            "ocr_extracted_value": 1000,
            "manual_value": 900,  # -10 %
            "comment": "Redressement interne",
        }
    ]
    flags = check_manual_override(decl, edits)
    assert len(flags) == 1 and flags[0]["severity"] == "low"
    assert flags[0]["evidence"]["comment"] == "Redressement interne"


def test_manual_override_ignores_non_material_fields():
    decl = {"id": 1}
    edits = [
        {
            "field_name": "adresse",
            "ocr_extracted_value": "X",
            "manual_value": "Y",
            "comment": "",
        }
    ]
    assert check_manual_override(decl, edits) == []


# ——— Rule B : revenue_mismatch ———


def test_revenue_mismatch_below_threshold_none():
    decl = {"chiffre_affaires_declare": 45000}
    summary = {"total_invoice_amount_ht": 47000, "invoice_ids": ["A", "B"]}
    assert check_revenue_invoice_mismatch(decl, summary, threshold_pct=20) is None


def test_revenue_mismatch_flags_and_lists_invoices():
    decl = {"chiffre_affaires_declare": 12000}
    summary = {"total_invoice_amount_ht": 47000, "invoice_ids": ["A", "B", "C"]}
    flag = check_revenue_invoice_mismatch(decl, summary)
    assert flag is not None
    assert flag["flag_type"] == "revenue_mismatch"
    assert flag["evidence"]["gap_amount"] == 35000
    assert flag["evidence"]["gap_percentage"] == 74.47
    assert flag["evidence"]["invoice_ids"] == ["A", "B", "C"]
    assert flag["severity"] == "high"


# ——— Rule C : sudden_drop ———


def test_sudden_drop_none_when_stable():
    current = {"year": 2026, "month": 9, "chiffre_affaires_declare": 40000}
    history = [
        {"year": 2026, "month": m, "chiffre_affaires_declare": 41000} for m in range(3, 9)
    ]
    assert check_sudden_drop(1, current, history) is None


def test_sudden_drop_flags_large_drop():
    current = {"year": 2026, "month": 9, "chiffre_affaires_declare": 12000}
    history = [
        {"year": 2026, "month": m, "chiffre_affaires_declare": 40000} for m in range(3, 9)
    ]
    flag = check_sudden_drop(1, current, history)
    assert flag is not None
    assert flag["flag_type"] == "sudden_drop"
    assert flag["evidence"]["historical_average"] == 40000
    assert flag["evidence"]["drop_percentage"] == 70.0
    assert flag["severity"] == "high"


def test_sudden_drop_suppressed_when_seasonal():
    # baisse le 09/2026 mais la même baisse existait déjà le 09/2025 → saisonnier
    current = {"year": 2026, "month": 9, "chiffre_affaires_declare": 12000}
    history = [
        {"year": 2026, "month": m, "chiffre_affaires_declare": 40000} for m in range(3, 9)
    ]
    history += [
        {"year": 2025, "month": 9, "chiffre_affaires_declare": 12000},
        {"year": 2025, "month": 8, "chiffre_affaires_declare": 40000},
        {"year": 2025, "month": 7, "chiffre_affaires_declare": 39000},
    ]
    assert check_sudden_drop(1, current, history) is None


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError:
            failed += 1
            print(f"FAIL  {fn.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} tests OK")
    raise SystemExit(1 if failed else 0)
