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
    stamp_duty_total: float = 0.0
    hotel_tax_base: float = 0.0
    hotel_tax_amount: float = 0.0
    etablissement_tax_base: float = 0.0
    etablissement_tax_amount: float = 0.0
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
    cif: CIFExtract | None = None
    rne: RNEExtract | None = None
    gap_questions: list[GapQuestion] = Field(default_factory=list)
    checklist: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    needs_user_review: list[str] = Field(default_factory=list)
    sources_summary: dict[str, Any] = Field(default_factory=dict)


class BuildFromScansRequest(BaseModel):
    month: MonthContext
    cif: CIFExtract | None = None
    rne: RNEExtract | None = None
    invoices: list[InvoiceExtract] = Field(default_factory=list)
    answers: dict[str, Any] = Field(default_factory=dict)
    amounts_override: FormAmounts | None = None


class BuildDeclarationRequest(BaseModel):
    """Compat + export final."""

    profile: TaxpayerProfile
    month: MonthContext
    amounts_override: FormAmounts | None = None
    invoices: list[InvoiceExtract] = Field(default_factory=list)
    cif: CIFExtract | None = None
    rne: RNEExtract | None = None
    answers: dict[str, Any] = Field(default_factory=dict)
