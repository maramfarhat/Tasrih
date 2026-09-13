from __future__ import annotations

from typing import Any

from app.declaration.models import (
    CIFExtract,
    FormAmounts,
    FilledForm,
    GapQuestion,
    InvoiceExtract,
    MonthContext,
    PayslipExtract,
    PersonType,
    RetenueLine,
    RNEExtract,
    Sector,
    TaxpayerProfile,
)
from app.declaration.applicability import (
    SECTOR_QUESTION,
    assess_taxes,
    checkboxes_from,
    detect_domain,
    sans_objet_labels,
)

# Taux légaux
TVA_RATES = (19.0, 13.0, 7.0)
TFP_RATE_MANUFACTURING = 0.01
TFP_RATE_STANDARD = 0.02
FOPROLOS_RATE = 0.01
STAMP_DUTY_UNIT = 1.0  # 1 DT par facture encaissée
HOTEL_TAX_RATE = 0.02


def _guess_sector(activity: str, legal_form: str = "") -> Sector:
    a = (activity or "").lower()
    if any(k in a for k in ("نزل", "hotel", "touris", "سياح")):
        return Sector.hotellerie
    if any(k in a for k in ("فلاحة", "agric", "صيد")):
        return Sector.agriculture
    if any(k in a for k in ("صناع", "industr", "تصنيع")):
        return Sector.industrie
    if any(k in a for k in ("association", "جمعية", "association")):
        return Sector.association
    if any(k in a for k in ("تجار", "commerce", "جملة", "wholesale")):
        return Sector.commerce
    if any(k in a for k in ("مهن", "avocat", "médecin", "conseil", "consult")):
        return Sector.profession_liberale
    if "خدمات" in a or "service" in a:
        return Sector.services
    if "sarl" in (legal_form or "").lower() or "ذات المسؤولية" in (legal_form or ""):
        return Sector.commerce
    return Sector.autre


def merge_profile(
    cif: CIFExtract | None,
    rne: RNEExtract | None,
    answers: dict[str, Any] | None = None,
) -> TaxpayerProfile:
    answers = answers or {}
    name = (cif.name if cif else None) or (rne.company_name if rne else None) or ""
    address = (cif.address if cif else None) or (rne.registered_address if rne else None) or ""
    activity = (cif.main_activity if cif else None) or (rne.main_activity if rne else None) or ""
    tax_id = (cif.tax_id if cif else None) or ""
    # Normalize tax id like 1290021/A or 1211124 A/P/M/000
    if tax_id and " " in tax_id and "/" not in tax_id.split()[0]:
        tax_id = tax_id.replace(" ", "/")

    subject_vat = True
    if cif and cif.subject_to_vat is not None:
        subject_vat = cif.subject_to_vat
    elif cif and cif.vat_status:
        subject_vat = "non assujetti" not in cif.vat_status.lower()

    sector = _guess_sector(
        activity,
        str(answers.get("legal_form") or (rne.legal_form if rne else "") or ""),
    )
    if answers.get("sector"):
        try:
            sector = Sector(answers["sector"])
        except ValueError:
            pass

    profile = TaxpayerProfile(
        name=str(answers.get("name") or name),
        address=str(answers.get("address") or address),
        postal_code=str(answers.get("postal_code") or ""),
        activity=str(answers.get("activity") or activity),
        tax_id=str(answers.get("tax_id") or tax_id),
        vat_code=str(answers.get("vat_code") or (cif.vat_code if cif else "") or ""),
        category_code=str(
            answers.get("category_code") or (cif.category_code if cif else "") or ""
        ),
        secondary_establishment=str(
            answers.get("secondary_establishment")
            or (cif.secondary_establishment if cif else None)
            or "000"
        ),
        person_type=PersonType.societe if rne else PersonType.physique,
        sector=sector,
        rne_identifier=str(answers.get("rne_identifier") or (rne.rne_identifier if rne else "") or "")
        or None,
        commercial_name=str(
            answers.get("commercial_name")
            or ((rne.commercial_name_latin or rne.commercial_name) if rne else "")
            or ""
        )
        or None,
        legal_form=str(answers.get("legal_form") or (rne.legal_form if rne else "") or "") or None,
        capital=rne.capital if rne else None,
        vat_status=str(answers.get("vat_status") or (cif.vat_status if cif else "") or "") or None,
        subject_to_vat=bool(answers["subject_to_vat"])
        if "subject_to_vat" in answers
        else subject_vat,
        has_employees=answers.get("has_employees"),
        does_withholding=answers.get("does_withholding"),
        subject_tfp=answers.get("subject_tfp"),
        subject_foprolos=answers.get("subject_foprolos"),
        subject_etablissement=answers.get("subject_etablissement"),
        subject_hotel_tax=answers.get("subject_hotel_tax"),
        is_manufacturing=answers.get("is_manufacturing"),
        totalement_exportatrice=answers.get("totalement_exportatrice"),
    )

    # Infer local taxes from sector if not answered
    if profile.subject_hotel_tax is None:
        profile.subject_hotel_tax = profile.sector == Sector.hotellerie
    # subject_etablissement reste None : l'applicabilité le déduit du domaine d'activité.
    if profile.has_employees is False:
        profile.subject_tfp = False
        profile.subject_foprolos = False
    elif profile.has_employees is True:
        if profile.subject_tfp is None:
            profile.subject_tfp = True
        if profile.subject_foprolos is None:
            profile.subject_foprolos = True
    # do not auto-set does_withholding from employees — asked explicitly later

    return profile


def aggregate_invoices(invoices: list[InvoiceExtract], profile: TaxpayerProfile) -> FormAmounts:
    ca = 0.0
    ca19 = 0.0
    ca13 = 0.0
    ca7 = 0.0
    tva = 0.0
    tva19 = 0.0
    tva_ded = 0.0
    stamp_count = 0
    pid = re_alnum(profile.tax_id or "")

    def salvage(inv: InvoiceExtract) -> InvoiceExtract:
        """Si HT/TVA absents, reparcourir raw_text_preview."""
        if inv.amount_ht and inv.vat_amount:
            return inv
        preview = inv.raw_text_preview or ""
        if len(preview) < 20:
            return inv
        try:
            from app.declaration.extract import _heuristic_invoice

            h = _heuristic_invoice(preview)
        except Exception:
            return inv
        data = inv.model_dump()
        for k, v in h.items():
            if k in data and v is not None and (data.get(k) in (None, 0, 0.0, "")):
                data[k] = v
        if h.get("amount_ht") and not data.get("amount_ht"):
            data["amount_ht"] = h["amount_ht"]
        if h.get("vat_amount") and not data.get("vat_amount"):
            data["vat_amount"] = h["vat_amount"]
        if h.get("stamp_duty") is not None:
            data["stamp_duty"] = h["stamp_duty"]
        data["direction"] = data.get("direction") or "vente"
        return InvoiceExtract(**data)

    for inv in invoices:
        inv = salvage(inv)
        ht = float(inv.amount_ht or 0.0)
        vat = float(inv.vat_amount or 0.0)
        # Timbre TN ~ 1 TND ; OCR lit souvent 1,000 → 1000 ou 3000
        stamp_raw = float(inv.stamp_duty or 0.0)
        if stamp_raw >= 500:
            stamp_raw = 1.0
        elif stamp_raw > 50:
            stamp_raw = 0.0

        direction = inv.direction
        vid = re_alnum(inv.vendor_tax_id or "")
        cid = re_alnum(inv.client_tax_id or "")
        if direction not in ("vente", "achat"):
            if pid and vid and pid in vid:
                direction = "vente"
            elif pid and cid and pid in cid:
                direction = "achat"
            else:
                direction = "vente"
        elif direction == "achat" and not (pid and cid and pid in cid):
            direction = "vente"

        rate = inv.vat_rate
        if rate is None and ht and vat:
            ratio = 100 * vat / ht
            # snap to Tunisian rates
            for candidate in (19, 13, 7, 0):
                if abs(ratio - candidate) < 1.5:
                    rate = float(candidate)
                    break

        if direction == "achat":
            # TVA déductible = somme des achats dans les factures reçues.
            tva_ded += vat
            continue

        ca += ht
        tva += vat
        # Droit de timbre : nombre de factures encaissées * 1 DT.
        stamp_count += 1
        if rate is not None and abs(rate - 19) < 0.6:
            ca19 += ht
            tva19 += vat
        elif rate is not None and abs(rate - 13) < 0.6:
            ca13 += ht
        elif rate is not None and abs(rate - 7) < 0.6:
            ca7 += ht
        # unknown rate: keep in CA total only — do not invent a 19% bucket

    # If everything taxed looks like a single 19% regime, attribute residual to 19%
    if ca and tva and ca19 == 0 and ca13 == 0 and ca7 == 0:
        ratio = 100 * tva / ca if ca else 0
        if abs(ratio - 19) < 2:
            ca19 = ca
            tva19 = tva

    solde_tva = tva - tva_ded
    if solde_tva > 0:
        tva_nette = solde_tva
        credit_next = 0.0
    else:
        # Crédit de TVA : reporté sur le mois suivant.
        tva_nette = 0.0
        credit_next = -solde_tva
    stamp_total = stamp_count * STAMP_DUTY_UNIT
    assess = assess_taxes(profile)
    etab_base = ca if assess["المعلوم_على_المؤسسات"].applicable else 0.0
    hotel_base = ca if assess["المعلوم_على_النزل"].applicable else 0.0
    return FormAmounts(
        ca_ht=round(ca, 3),
        ca_ht_19=round(ca19, 3),
        ca_ht_13=round(ca13, 3),
        ca_ht_7=round(ca7, 3),
        tva_collectee=round(tva, 3),
        tva_collectee_19=round(tva19, 3),
        tva_deductible=round(tva_ded, 3),
        tva_nette=round(tva_nette, 3),
        tva_credit_next=round(credit_next, 3),
        retenues_total=0.0,
        stamp_duty_count=stamp_count,
        stamp_duty_total=round(stamp_total, 3),
        hotel_tax_base=round(hotel_base, 3),
        hotel_tax_rate=HOTEL_TAX_RATE,
        hotel_tax_amount=round(hotel_base * HOTEL_TAX_RATE, 3) if hotel_base else 0.0,
        etablissement_tax_base=round(etab_base, 3),
        etablissement_tax_amount=round(etab_base * 0.001, 3) if etab_base else 0.0,
        other_notes="Montants agrégés depuis factures TEIF / importées",
    )


def payroll_total(payslips: list[PayslipExtract]) -> float:
    total = 0.0
    for slip in payslips:
        if slip.salaire_brut:
            total += float(slip.salaire_brut)
    return round(total, 3)


def apply_payroll(
    amounts: FormAmounts,
    profile: TaxpayerProfile,
    payslips: list[PayslipExtract],
) -> FormAmounts:
    """Calcule la masse salariale brute puis TFP et FOPROLOS.

    - TFP : base = masse salariale brute, 1% si industrie manufacturière sinon 2%.
    - FOPROLOS : base = masse salariale brute, 1% (sauf totalement exportatrice).
    """
    masse = payroll_total(payslips)
    if masse <= 0 and amounts.masse_salariale_brute:
        masse = float(amounts.masse_salariale_brute)
    amounts.masse_salariale_brute = round(masse, 3)

    if profile.subject_tfp and masse:
        rate = TFP_RATE_MANUFACTURING if profile.is_manufacturing else TFP_RATE_STANDARD
        amounts.tfp_base = round(masse, 3)
        amounts.tfp_rate = rate
        amounts.tfp_amount = round(masse * rate, 3)

    if profile.subject_foprolos and masse and not profile.totalement_exportatrice:
        amounts.foprolos_base = round(masse, 3)
        amounts.foprolos_rate = FOPROLOS_RATE
        amounts.foprolos_amount = round(masse * FOPROLOS_RATE, 3)
    elif profile.totalement_exportatrice:
        amounts.foprolos_amount = 0.0
    return amounts


def apply_retenues(amounts: FormAmounts, retenues: list[RetenueLine]) -> FormAmounts:
    """Retenue à la source : total des certificats TEJ (assiette + montant)."""
    total = 0.0
    base = 0.0
    for line in retenues:
        line_base = float(line.base or 0.0)
        base += line_base
        if line.amount:
            total += float(line.amount)
        elif line.rate and line_base:
            # Taux saisi en pourcentage (10, 15, 1.5) ou en fraction (0.10).
            factor = line.rate / 100.0 if line.rate >= 1 else line.rate
            total += line_base * factor
    amounts.retenue_base_total = round(base, 3)
    amounts.retenues_total = round(total, 3)
    return amounts


def re_alnum(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalnum())


def checkboxes_for(profile: TaxpayerProfile) -> dict[str, bool]:
    """Cases de taxes du formulaire, déduites du domaine d'activité."""
    return checkboxes_from(assess_taxes(profile))


def compute_gaps(
    profile: TaxpayerProfile,
    cif: CIFExtract | None,
    rne: RNEExtract | None,
    invoices: list[InvoiceExtract],
    answers: dict[str, Any],
) -> list[GapQuestion]:
    """Questions bloquantes avant l'ouverture de la déclaration mensuelle."""
    gaps: list[GapQuestion] = []
    if profile.does_withholding is None and "does_withholding" not in answers:
        gaps.append(
            GapQuestion(
                id="does_withholding",
                field="does_withholding",
                type="boolean",
                question_fr="Avez-vous effectué des retenues à la source ?",
                options=[
                    {"value": True, "label": "Oui"},
                    {"value": False, "label": "Non"},
                ],
            )
        )
    if (
        profile.subject_tfp
        and profile.is_manufacturing is None
        and "is_manufacturing" not in answers
    ):
        gaps.append(
            GapQuestion(
                id="is_manufacturing",
                field="is_manufacturing",
                type="boolean",
                question_fr="Activité industrielle manufacturière (TFP 1%) ?",
                question_ar="هل النشاط صناعي تحويلي (ط.ت.م 1%)؟",
                options=[
                    {"value": True, "label": "Oui — TFP 1%"},
                    {"value": False, "label": "Non — TFP 2%"},
                ],
            )
        )
    if (
        profile.subject_foprolos
        and profile.totalement_exportatrice is None
        and "totalement_exportatrice" not in answers
    ):
        gaps.append(
            GapQuestion(
                id="totalement_exportatrice",
                field="totalement_exportatrice",
                type="boolean",
                question_fr="Entreprise totalement exportatrice (exonération FOPROLOS) ?",
                question_ar="هل المؤسسة مصدّرة كليا (إعفاء من صندوق النهوض بالمسكن)؟",
                options=[
                    {"value": True, "label": "Oui — exonérée"},
                    {"value": False, "label": "Non — FOPROLOS 1%"},
                ],
            )
        )
    # Domaine d'activité : s'il n'est pas déductible, une seule question suffit à
    # éliminer toutes les taxes non applicables.
    if detect_domain(profile) in ("autre", "") and "sector" not in answers:
        gaps.append(
            GapQuestion(
                id=SECTOR_QUESTION["id"],
                field=SECTOR_QUESTION["field"],
                type="select",
                question_fr=SECTOR_QUESTION["question_fr"],
                question_ar=SECTOR_QUESTION["question_ar"],
                options=list(SECTOR_QUESTION["options"]),
                required=False,
            )
        )
    return gaps


def build_from_scans(
    month: MonthContext,
    cif: CIFExtract | None = None,
    rne: RNEExtract | None = None,
    invoices: list[InvoiceExtract] | None = None,
    retenues: list[RetenueLine] | None = None,
    payslips: list[PayslipExtract] | None = None,
    answers: dict[str, Any] | None = None,
    amounts_override: FormAmounts | None = None,
) -> FilledForm:
    invoices = invoices or []
    retenues = retenues or []
    payslips = payslips or []
    answers = answers or {}
    profile = merge_profile(cif, rne, answers)
    if amounts_override is not None:
        amounts = amounts_override
        # Les overrides manuels ne doivent pas écraser un calcul absent.
        if amounts.tva_nette == 0 and amounts.tva_collectee and not amounts.tva_deductible:
            amounts.tva_nette = amounts.tva_collectee
    else:
        amounts = aggregate_invoices(invoices, profile)
    # Les listes de certificats / fiches de paie sont autoritatives ; à défaut on
    # conserve les montants saisis manuellement dans amounts_override.
    if retenues:
        amounts = apply_retenues(amounts, retenues)
    if payslips or (
        amounts.masse_salariale_brute and (profile.subject_tfp or profile.subject_foprolos)
    ):
        amounts = apply_payroll(amounts, profile, payslips)
    boxes = checkboxes_for(profile)
    assessment = assess_taxes(profile)
    domain = detect_domain(profile)
    sans_objet = sans_objet_labels(assessment)
    gaps = compute_gaps(profile, cif, rne, invoices, answers)

    # Filter answered optional flags
    gaps = [g for g in gaps if g.field not in answers]

    sections = ["identite", "periode"]
    if boxes.get("خصم_من_المورد"):
        sections.append("retenues")
    if boxes.get("الأداء_على_التكوين_المهني"):
        sections.append("tfp")
    if boxes.get("صندوق_النهوض_بالمسكن"):
        sections.append("foprolos")
    if boxes.get("الأداء_على_القيمة_المضافة"):
        sections.append("tva")
    if boxes.get("معلوم_الطابع_الجبائي"):
        sections.append("timbre")
    if boxes.get("المعلوم_على_المؤسسات"):
        sections.append("maalum_etablissement")
    if boxes.get("المعلوم_على_النزل"):
        sections.append("maalum_hotel")

    needs: list[str] = []
    if not profile.tax_id:
        needs.append("المعرف الجبائي manquant")
    if profile.subject_to_vat and amounts.tva_collectee == 0 and invoices:
        needs.append("TVA nulle malgré factures — vérifier direction vente/achat")
    if not invoices and answers.get("invoices_missing") is not True:
        needs.append("Pas de factures électroniques agrégées")
    if boxes.get("خصم_من_المورد") and not retenues and not amounts.retenues_total:
        needs.append("Retenue à la source : aucun certificat TEJ importé")
    if boxes.get("الأداء_على_التكوين_المهني") and not amounts.tfp_amount:
        needs.append("TFP : masse salariale brute à confirmer (fiches de paie)")
    if boxes.get("صندوق_النهوض_بالمسكن") and not amounts.foprolos_amount:
        if not profile.totalement_exportatrice:
            needs.append("FOPROLOS : masse salariale brute à confirmer (fiches de paie)")
    for inv in invoices:
        if inv.confidence < 0.5:
            needs.append(f"Facture peu confiante: {inv.filename}")
    for slip in payslips:
        if slip.confidence < 0.5:
            needs.append(f"Fiche de paie peu confiante: {slip.filename or slip.employee_name or '?'}")

    confidences = [c.confidence for c in ([cif] if cif else []) + ([rne] if rne else [])]
    confidences += [i.confidence for i in invoices]
    conf = sum(confidences) / len(confidences) if confidences else 0.4
    if gaps:
        conf = max(0.25, conf - 0.08 * len(gaps))

    return FilledForm(
        profile=profile,
        month=month,
        active_sections=sections,
        checkboxes=boxes,
        amounts=amounts,
        invoices=invoices,
        retenues=retenues,
        payslips=payslips,
        cif=cif,
        rne=rne,
        gap_questions=gaps,
        checklist=[
            "Vérifier identité (CIF + RNE) sur page 1",
            "Vérifier cases (x) TVA / retenues / locaux",
            "Contrôler CA HT et TVA 19% sur page TVA",
            "Contrôler معلوم المؤسسات / نزل si applicable",
            "Déposer uniquement après validation humaine",
        ],
        confidence=round(conf, 2),
        needs_user_review=needs,
        sources_summary={
            "cif": bool(cif),
            "rne": bool(rne),
            "invoices": len(invoices),
            "retenues": len(retenues),
            "payslips": len(payslips),
            "fatoora": True,
        },
        domain=domain,
        tax_applicability={k: a.applicable for k, a in assessment.items()},
        tax_lines=[a.as_dict() for a in assessment.values()],
        sans_objet=sans_objet,
    )


# legacy export for old callers
def build_filled_form(profile, month, invoices=None, amounts_override=None):
    return build_from_scans(
        month=month,
        invoices=invoices or [],
        answers={
            "name": profile.name,
            "address": profile.address,
            "tax_id": profile.tax_id,
            "subject_to_vat": profile.subject_to_vat,
            "has_employees": profile.has_employees,
            "does_withholding": profile.does_withholding,
            "sector": profile.sector.value if hasattr(profile.sector, "value") else profile.sector,
        },
        amounts_override=amounts_override,
    )


STATUS_QUESTIONS: list[dict] = []  # remplacé par gap_questions dynamiques
