"""Jeu de données de démonstration pour la vue DGI (/admin).

Remplit enterprises / declarations / invoices_summary / field_edits puis lance la
détection, afin que le tableau de bord soit vivant en démo. N'agit qu'une fois
(si la table businesses est vide).
"""

from __future__ import annotations

from app import admin_db
from app.services import fraud

# (matricule, nom, activité, régime, [(mois, CA, tva_col, tva_ded, retenue)], invoices HT 09, edits)
_DEMO = [
    {
        "matricule": "1290021/A",
        "name": "STECOM",
        "activite": "Commerce de gros — équipements",
        "regime": "reel",
        "months": {
            3: 40000, 4: 38000, 5: 42000, 6: 39500, 7: 41000, 8: 40500, 9: 12000,
        },
        "invoices_ht_09": 47000,
        "invoices_ids": ["TEIF-2026-0901", "TEIF-2026-0902", "TEIF-2026-0903"],
        "edits": [("tva_collectee", 8200, 3100, "Facture annulée après export, non incluse dans le calcul OCR")],
        "tva": lambda ca: round(ca * 0.19, 3),
    },
    {
        "matricule": "1234567/A",
        "name": "SERVICES CONSEIL SARL",
        "activite": "Services / conseil / informatique",
        "regime": "reel",
        "months": {3: 15000, 4: 15500, 5: 14800, 6: 16200, 7: 15900, 8: 16100, 9: 16000},
        "invoices_ht_09": 16000,
        "invoices_ids": ["TEIF-2026-0910", "TEIF-2026-0911"],
        "edits": [],
        "tva": lambda ca: round(ca * 0.19, 3),
    },
    {
        "matricule": "2233445/B",
        "name": "CIMENTS DU SUD",
        "activite": "Industrie / fabrication",
        "regime": "reel",
        "months": {
            3: 90000, 4: 88000, 5: 92000, 6: 95000, 7: 91000, 8: 93000, 9: 30000,
        },
        "invoices_ht_09": 32000,
        "invoices_ids": ["TEIF-2026-0920", "TEIF-2026-0921"],
        "edits": [],
        "tva": lambda ca: round(ca * 0.19, 3),
    },
    {
        "matricule": "4455667/C",
        "name": "HOTEL MER & SPA",
        "activite": "Hôtellerie / tourisme",
        "regime": "reel",
        "months": {3: 20000, 4: 25000, 5: 30000, 6: 45000, 7: 60000, 8: 65000, 9: 18000},
        "invoices_ht_09": 52000,
        "invoices_ids": ["TEIF-2026-0930", "TEIF-2026-0931", "TEIF-2026-0932"],
        "edits": [],
        "tva": lambda ca: round(ca * 0.07, 3),
    },
    {
        "matricule": "5566778/D",
        "name": "FERME AGRI BIO",
        "activite": "Agriculture / pêche",
        "regime": "forfaitaire",
        "months": {3: 6000, 4: 6500, 5: 7000, 6: 7200, 7: 6800, 8: 7100, 9: 6900},
        "invoices_ht_09": 0,
        "invoices_ids": [],
        "edits": [],
        "tva": lambda ca: 0.0,
    },
    {
        "matricule": "6677889/E",
        "name": "TECH WEB SARL",
        "activite": "Services / informatique",
        "regime": "reel",
        "months": {3: 12000, 4: 13000, 5: 12500, 6: 14000, 7: 13500, 8: 13800, 9: 5000},
        "invoices_ht_09": 5200,
        "invoices_ids": ["TEIF-2026-0940"],
        "edits": [
            ("chiffre_affaires_declare", 13800, 5000, "Client résilié, avoir émis"),
            ("tva_collectee", 2622, 950, ""),
        ],
        "tva": lambda ca: round(ca * 0.19, 3),
    },
]

_STATUS = {3: "paid", 4: "paid", 5: "paid", 6: "submitted", 7: "submitted", 8: "submitted", 9: "prepared"}


def seed_admin_demo() -> bool:
    """Retourne True si des données de démo ont été créées."""
    with admin_db.connect() as conn:  # type: ignore[attr-defined]
        n = conn.execute("SELECT COUNT(*) AS n FROM businesses").fetchone()["n"]
    if n:
        return False

    for b in _DEMO:
        business_id = admin_db.upsert_business(
            matricule_fiscal=b["matricule"],
            activite=b["activite"],
            regime=b["regime"],
            name=b["name"],
        )
        for month, ca in b["months"].items():
            tva = b["tva"](ca)
            admin_db.upsert_declaration(
                business_id=business_id,
                month=month,
                year=2026,
                chiffre_affaires_declare=ca,
                tva_collectee=tva,
                tva_deductible=round(tva * 0.4, 3),
                retenue_totale=0,
                status=_STATUS.get(month, "prepared"),
            )
        if b["invoices_ht_09"]:
            admin_db.upsert_invoices_summary(
                business_id=business_id,
                month=9,
                year=2026,
                total_invoice_count=len(b["invoices_ids"]),
                total_invoice_amount_ht=b["invoices_ht_09"],
                total_invoice_amount_ttc=round(b["invoices_ht_09"] * 1.19, 3),
                invoice_ids=b["invoices_ids"],
            )
        decl = admin_db.declaration_for_period(business_id, 2026, 9)
        for field_name, ocr, manual, comment in b["edits"]:
            if decl:
                admin_db.add_field_edit(decl["id"], field_name, ocr, manual, comment)

    fraud.run_detection_all()
    return True
