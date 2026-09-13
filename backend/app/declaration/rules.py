from __future__ import annotations

from app.declaration.models import (
    FilledForm,
    FormAmounts,
    InvoiceExtract,
    MonthContext,
    Sector,
    TaxpayerProfile,
)


def active_sections_for(profile: TaxpayerProfile) -> list[str]:
    sections = ["identite", "periode"]
    if profile.does_withholding or profile.has_employees:
        sections.append("retenues")
    if profile.subject_to_vat:
        sections.append("tva")
    if profile.subject_tfp:
        sections.append("tfp")
    if profile.subject_foprolos:
        sections.append("foprolos")
    if profile.subject_etablissement or profile.sector in {
        Sector.commerce,
        Sector.industrie,
        Sector.services,
        Sector.profession_liberale,
    }:
        sections.append("maalum_etablissement")
    if profile.subject_hotel_tax or profile.sector == Sector.hotellerie:
        sections.append("maalum_hotel")
    if profile.subject_licence:
        sections.append("maalum_ijaza")
    if profile.sector == Sector.agriculture and not profile.subject_to_vat:
        sections.append("agriculture_note")
    return sections


def checkboxes_for(profile: TaxpayerProfile) -> dict[str, bool]:
    return {
        "خصم_من_المورد": profile.does_withholding or profile.has_employees,
        "الأداء_على_التكوين_المهني": profile.subject_tfp,
        "صندوق_النهوض_بالمسكن": profile.subject_foprolos,
        "المعلوم_على_الاستهلاك": False,
        "الأداء_على_القيمة_المضافة": profile.subject_to_vat,
        "معاليم_أخرى_على_رقم_المعاملات": False,
        "معلوم_الطابع_الجبائي": False,
        "المعلوم_على_المؤسسات": profile.subject_etablissement
        or profile.sector
        in {
            Sector.commerce,
            Sector.industrie,
            Sector.services,
            Sector.profession_liberale,
        },
        "المعلوم_على_النزل": profile.subject_hotel_tax
        or profile.sector == Sector.hotellerie,
        "معلوم_الإجازة": profile.subject_licence,
    }


def aggregate_from_invoices(invoices: list[InvoiceExtract]) -> FormAmounts:
    ca = 0.0
    tva = 0.0
    ttc = 0.0
    for inv in invoices:
        if inv.amount_ht is not None:
            ca += inv.amount_ht
        if inv.vat_amount is not None:
            tva += inv.vat_amount
        if inv.amount_ttc is not None:
            ttc += inv.amount_ttc
        elif inv.amount_ht is not None and inv.vat_amount is not None:
            ttc += inv.amount_ht + inv.vat_amount
    # Si uniquement TTC connu
    if ca == 0 and ttc > 0 and tva == 0:
        # approx 19% — à confirmer par l'utilisateur
        ca = round(ttc / 1.19, 3)
        tva = round(ttc - ca, 3)
    return FormAmounts(
        ca_ht=round(ca, 3),
        tva_collectee=round(tva, 3),
        tva_deductible=0.0,
        tva_nette=round(tva, 3),
        retenues_total=0.0,
        hotel_tax_base=0.0,
        hotel_tax_amount=0.0,
        etablissement_tax_base=round(ca, 3) if ca else 0.0,
        etablissement_tax_amount=0.0,
        other_notes="Montants agrégés depuis fatourat — à vérifier",
    )


def build_filled_form(
    profile: TaxpayerProfile,
    month: MonthContext,
    invoices: list[InvoiceExtract] | None = None,
    amounts_override: FormAmounts | None = None,
) -> FilledForm:
    invoices = invoices or []
    amounts = amounts_override or aggregate_from_invoices(invoices)
    sections = active_sections_for(profile)
    boxes = checkboxes_for(profile)

    # Hôtel: base = CA si non précisé
    if boxes.get("المعلوم_على_النزل") and amounts.hotel_tax_base == 0 and amounts.ca_ht:
        amounts.hotel_tax_base = amounts.ca_ht

    needs: list[str] = []
    if not profile.tax_id:
        needs.append("المعرف الجبائي manquant")
    if profile.subject_to_vat and amounts.tva_collectee == 0 and not invoices:
        needs.append("Aucun montant TVA — saisissez ou scannez des fatourat")
    if boxes.get("المعلوم_على_النزل") and amounts.hotel_tax_amount == 0:
        needs.append("معلوم على النزل : montant à confirmer (taux local)")
    if boxes.get("المعلوم_على_المؤسسات") and amounts.etablissement_tax_amount == 0:
        needs.append("معلوم على المؤسسات : montant à confirmer selon commune")
    for inv in invoices:
        if inv.confidence < 0.55:
            needs.append(f"Fatoura peu confiante : {inv.filename}")

    checklist = [
        "Vérifier nom, adresse, المعرف الجبائي",
        "Vérifier الشهر / السنة et رمز التصريح",
        "Contrôler les cases (x) selon l’activité",
        "Contrôler tous les montants avant dépôt / télédeclaration",
        "Conserver les fatourat scannées comme justificatifs",
    ]
    if profile.sector == Sector.agriculture:
        checklist.append(
            "Agriculture : confirmer si une déclaration mensuelle est réellement due ce mois"
        )

    conf = 0.85
    if needs:
        conf = max(0.35, 0.85 - 0.08 * len(needs))
    if invoices:
        conf = min(conf, sum(i.confidence for i in invoices) / len(invoices))

    return FilledForm(
        profile=profile,
        month=month,
        active_sections=sections,
        checkboxes=boxes,
        amounts=amounts,
        invoices=invoices,
        checklist=checklist,
        confidence=round(conf, 2),
        needs_user_review=needs,
    )


STATUS_QUESTIONS: list[dict] = [
    {
        "id": "person_type",
        "question_fr": "Vous êtes ?",
        "question_ar": "هل أنت؟",
        "options": [
            {"value": "physique", "label": "Personne physique / شخص طبيعي"},
            {"value": "societe", "label": "Société / شخص معنوي"},
        ],
    },
    {
        "id": "sector",
        "question_fr": "Secteur principal ?",
        "question_ar": "ما هو نشاطك الرئيسي؟",
        "options": [
            {"value": "agriculture", "label": "Agriculture / فلاحة"},
            {"value": "hotellerie", "label": "Hôtellerie / نزل"},
            {"value": "commerce", "label": "Commerce / تجارة"},
            {"value": "industrie", "label": "Industrie / صناعة"},
            {"value": "services", "label": "Services"},
            {"value": "profession_liberale", "label": "Profession libérale"},
            {"value": "autre", "label": "Autre"},
        ],
    },
    {
        "id": "subject_to_vat",
        "question_fr": "Assujetti à la TVA ?",
        "question_ar": "هل أنت خاضع للأداء على القيمة المضافة؟",
        "options": [
            {"value": True, "label": "Oui / نعم"},
            {"value": False, "label": "Non / لا"},
        ],
    },
    {
        "id": "has_employees",
        "question_fr": "Avez-vous des salariés ?",
        "question_ar": "هل لديك أجراء؟",
        "options": [
            {"value": True, "label": "Oui"},
            {"value": False, "label": "Non"},
        ],
    },
    {
        "id": "does_withholding",
        "question_fr": "Faites-vous des retenues à la source ?",
        "question_ar": "هل تقوم بالخصم من المورد؟",
        "options": [
            {"value": True, "label": "Oui"},
            {"value": False, "label": "Non"},
        ],
    },
]
