"""
Tasrih — modèles pour le flux CIF + RNE + Fatoora → déclaration mensuelle.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class PersonType(str, Enum):
    physique = "physique"
    societe = "societe"


class TaxRegime(str, Enum):
    reel = "reel"
    forfaitaire = "forfaitaire"
    autre = "autre"


class Sector(str, Enum):
    agriculture = "agriculture"
    hotellerie = "hotellerie"
    commerce = "commerce"
    industrie = "industrie"
    services = "services"
    profession_liberale = "profession_liberale"
    association = "association"
    autre = "autre"


class DeclarationCode(str, Enum):
    automatique = "0"
    taswiya = "1"
    correction = "2"
    emploi_obligatoire = "3"
    arret_activite = "4"


class CIFExtract(BaseModel):
    """Carte d'identification fiscale."""

    tax_id: str | None = None
    vat_code: str | None = None
    category_code: str | None = None
    secondary_establishment: str | None = None
    name: str | None = None
    main_activity: str | None = None
    secondary_activity: str | None = None
    address: str | None = None
    activity_start_date: str | None = None
    vat_status: str | None = None  # ex. Assujetti Partiel A La TVA
    subject_to_vat: bool | None = None
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    raw_text_preview: str = ""


class RNEExtract(BaseModel):
    """Extrait Registre National des Entreprises."""

    rne_identifier: str | None = None
    old_commercial_register: str | None = None
    company_name: str | None = None
    commercial_name: str | None = None
    commercial_name_latin: str | None = None
    legal_form: str | None = None
    capital: float | None = None
    registered_address: str | None = None
    main_activity: str | None = None
    activity_code: str | None = None
    company_status: str | None = None
    registration_date: str | None = None
    activity_start_date: str | None = None
    branches_count: int | None = None
    person_type: PersonType = PersonType.societe
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    raw_text_preview: str = ""


class InvoiceLine(BaseModel):
    designation: str | None = None
    quantity: float | None = None
    unit_price_ht: float | None = None
    vat_rate: float | None = None
    amount_ht: float | None = None
    vat_amount: float | None = None


class PayslipExtract(BaseModel):
    """Fiche de paie (bulletin de salaire) d'un salarié."""

    filename: str = ""
    employee_name: str | None = None
    period: str | None = None
    salaire_brut: float | None = None
    cotisations: float | None = None
    salaire_net: float | None = None
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class RetenueLine(BaseModel):
    """Ligne de retenue à la source (certificat TEJ / XML)."""

    certificate_number: str | None = None
    beneficiary: str | None = None
    beneficiary_tax_id: str | None = None
    nature: str | None = None
    base: float = 0.0
    rate: float | None = None
    amount: float = 0.0
    period: str | None = None
    source: str = "tej_xml"
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)


class RetenueOperation(BaseModel):
    """Opération d'un certificat de retenue (schema TEJ DeclarationsRS)."""

    id_type_operation: str | None = None
    nature: str | None = None
    annee_facturation: str | None = None
    montant_ht: float = 0.0
    taux_rs: float | None = None
    taux_tva: float | None = None
    montant_tva: float = 0.0
    montant_ttc: float = 0.0
    montant_rs: float = 0.0
    montant_net_servi: float = 0.0


class RetenueCertificate(BaseModel):
    """Certificat de retenue à la source (un bénéficiaire)."""

    reference: str | None = None
    date_paiement: str | None = None
    resident: bool = True
    beneficiary_name: str | None = None
    beneficiary_id: str | None = None
    beneficiary_id_type: str | None = None
    beneficiary_category: str | None = None  # PM | PP
    beneficiary_address: str | None = None
    beneficiary_activity: str | None = None
    operations: list[RetenueOperation] = Field(default_factory=list)
    total_ht: float = 0.0
    total_tva: float = 0.0
    total_ttc: float = 0.0
    total_rs: float = 0.0
    total_net_servi: float = 0.0


class RetenueDeclaration(BaseModel):
    """Déclaration de retenue à la source TEJ (fichier DeclarationsRS)."""

    declarant_id: str | None = None
    declarant_category: str | None = None  # PM | PP
    declarant_name: str | None = None
    acte_depot: str | None = None  # 0 initial, 1 rectificative, …
    year: int | None = None
    month: int | None = None
    certificates: list[RetenueCertificate] = Field(default_factory=list)
    total_ht: float = 0.0
    total_tva: float = 0.0
    total_ttc: float = 0.0
    total_rs: float = 0.0
    total_net_servi: float = 0.0
    filename: str = ""


class InvoiceExtract(BaseModel):
    """Facture électronique (Fatoora / TTN)."""

    filename: str
    invoice_number: str | None = None
    invoice_date: str | None = None
    ttn_reference: str | None = None
    vendor: str | None = None
    vendor_tax_id: str | None = None
    client: str | None = None
    client_tax_id: str | None = None
    amount_ht: float | None = None
    vat_rate: float | None = None
    vat_amount: float | None = None
    amount_ttc: float | None = None
    stamp_duty: float | None = None
    net_to_pay: float | None = None
    currency: str = "TND"
    direction: str | None = None  # vente | achat
    lines: list[InvoiceLine] = Field(default_factory=list)
    category_guess: str | None = None
    confidence: float = 0.0
    warnings: list[str] = Field(default_factory=list)
    raw_text_preview: str = ""


class TaxpayerProfile(BaseModel):
    name: str = ""
    address: str = ""
    postal_code: str = ""
    activity: str = ""
    tax_id: str = ""
    vat_code: str = ""
    category_code: str = ""
    secondary_establishment: str = "000"
    person_type: PersonType = PersonType.societe
    regime: TaxRegime = TaxRegime.reel
    sector: Sector = Sector.commerce
    rne_identifier: str | None = None
    commercial_name: str | None = None
    legal_form: str | None = None
    capital: float | None = None
    vat_status: str | None = None
    has_employees: bool | None = None
    does_withholding: bool | None = None
    subject_to_vat: bool = True
    subject_tfp: bool | None = None
    subject_foprolos: bool | None = None
    subject_etablissement: bool | None = None
    subject_hotel_tax: bool | None = None
    subject_licence: bool = False
    # TFP : 1% si industrie manufacturière, 2% sinon.
    is_manufacturing: bool | None = None
    # FOPROLOS : exonération des entreprises totalement exportatrices sous conditions.
    totalement_exportatrice: bool | None = None


class MonthContext(BaseModel):
    year: int = Field(..., ge=2020, le=2100)
    month: int = Field(..., ge=1, le=12)
    declaration_code: DeclarationCode = DeclarationCode.automatique
    activity_stop_date: str | None = None


class FormAmounts(BaseModel):
    ca_ht: float = 0.0
    ca_ht_19: float = 0.0
    ca_ht_13: float = 0.0
    ca_ht_7: float = 0.0
    tva_collectee: float = 0.0
    tva_collectee_19: float = 0.0
    tva_deductible: float = 0.0
    tva_nette: float = 0.0
    retenues_total: float = 0.0
    retenue_base_total: float = 0.0
    # Masse salariale brute (issue des fiches de paie scannées)
    masse_salariale_brute: float = 0.0
    # TFP — Taxe de formation professionnelle (1% industrie manufacturière, 2% autres)
    tfp_base: float = 0.0
    tfp_rate: float = 0.0
    tfp_amount: float = 0.0
    # FOPROLOS — Fonds de promotion du logement pour les salariés (1%)
    foprolos_base: float = 0.0
    foprolos_rate: float = 0.01
    foprolos_amount: float = 0.0
    # Droit de timbre : nombre de factures encaissées * 1 DT
    stamp_duty_count: int = 0
    stamp_duty_total: float = 0.0
    # Taxe hôtelière : CA brut * 2%
    hotel_tax_base: float = 0.0
    hotel_tax_rate: float = 0.02
    hotel_tax_amount: float = 0.0
    etablissement_tax_base: float = 0.0
    etablissement_tax_amount: float = 0.0
    # Crédit de TVA
    tva_credit_report: float = 0.0  # crédit du mois précédent imputé
    tva_credit_next: float = 0.0  # crédit à reporter au mois suivant
    other_notes: str = ""


class GapQuestion(BaseModel):
    id: str
    question_fr: str
    question_ar: str = ""
    field: str
    type: str = "boolean"  # boolean | text | number | select
    options: list[dict[str, Any]] = Field(default_factory=list)
    required: bool = True


class FilledForm(BaseModel):
    profile: TaxpayerProfile
    month: MonthContext
    active_sections: list[str]
    checkboxes: dict[str, bool]
    amounts: FormAmounts
    invoices: list[InvoiceExtract] = Field(default_factory=list)
    retenues: list[RetenueLine] = Field(default_factory=list)
    payslips: list[PayslipExtract] = Field(default_factory=list)
    cif: CIFExtract | None = None
    rne: RNEExtract | None = None
    gap_questions: list[GapQuestion] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    needs_user_review: list[str] = Field(default_factory=list)
    sources_summary: dict[str, Any] = Field(default_factory=dict)
    # Domaine d'activité détecté + applicabilité de chaque taxe du formulaire.
    domain: str = ""
    tax_applicability: dict[str, bool] = Field(default_factory=dict)
    tax_lines: list[dict[str, Any]] = Field(default_factory=list)
    sans_objet: list[str] = Field(default_factory=list)


class BuildFromScansRequest(BaseModel):
    month: MonthContext
    cif: CIFExtract | None = None
    rne: RNEExtract | None = None
    invoices: list[InvoiceExtract] = Field(default_factory=list)
    retenues: list[RetenueLine] = Field(default_factory=list)
    payslips: list[PayslipExtract] = Field(default_factory=list)
    answers: dict[str, Any] = Field(default_factory=dict)
    amounts_override: FormAmounts | None = None


class RetenueExportRequest(BaseModel):
    """Export du PDF « Retenue à la source » depuis une déclaration TEJ."""

    declaration: RetenueDeclaration
    profile: TaxpayerProfile | None = None
    month: MonthContext | None = None


class BuildDeclarationRequest(BaseModel):
    """Compat + export final."""

    profile: TaxpayerProfile
    month: MonthContext
    amounts_override: FormAmounts | None = None
    invoices: list[InvoiceExtract] = Field(default_factory=list)
    retenues: list[RetenueLine] = Field(default_factory=list)
    payslips: list[PayslipExtract] = Field(default_factory=list)
    cif: CIFExtract | None = None
    rne: RNEExtract | None = None
    answers: dict[str, Any] = Field(default_factory=dict)
