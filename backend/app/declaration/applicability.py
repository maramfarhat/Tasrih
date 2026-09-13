"""Applicabilité des impôts / taxes de la déclaration mensuelle.

Le formulaire officiel « Déclaration mensuelle » comporte une ligne de cases
(types d'impôts) et plusieurs rubriques dont beaucoup ne concernent qu'une
activité précise (nuitées, alcool, tabac, ciment, tourisme, agriculture…).

Plutôt que de laisser l'utilisateur répondre à toutes les rubriques, on déduit
le **domaine d'activité** (CIF / RNE / réponses) et on marque les taxes non
applicables « sans objet » (X) au lieu de les remplir.

Le référentiel est volontairement data-driven : une liste de `TaxDef` avec un
prédicat `applies(profile, blob)`.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Callable

from app.declaration.models import Sector, TaxpayerProfile


def _norm(text: str | None) -> str:
    """Minuscule, sans accents, espaces compactés (laisse l'arabe intact)."""
    s = (text or "").lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


# —— mots-clés par domaine ————————————————————————————————————————————————
_KW = {
    "hotellerie": ("nuit", "heberg", "hotel", "نزل", "إيواء", "ايواء", "resort", "maison d'hote"),
    "tourisme": ("touris", "voyage", "سفر", "سياح", "agence de voyage", "loisir"),
    "alcool": (
        "alcool", "biere", "vin", "boisson", "spiritueux", "liquor", "bar", "pub",
        "كحول", "خمر", "مشروب", "بيرة",
    ),
    "tabac": ("tabac", "cigare", "cigarette", "تبغ", "دخان", "معسل"),
    "ciment": ("ciment", "cement", "اسمنت", "إسمنت", "خرسان", "beton", "حجارة"),
    "agri": ("agric", "فلاح", "زراع", "peche", "صيد", "زيتون", "بيولوج", "élevage", "elevage", "مواشي"),
    "industrie": ("industr", "صناع", "manufact", "usine", "تجهيز", "تصنيع", "معمل", "mecaniq", "mécanique"),
    "commerce": ("commerce", "vente", "تجار", "جملة", "détail", "detail", "بيوع", "import", "export", "توزيع"),
    "services": (
        "service", "خدمات", "conseil", "consult", "informat", "logiciel", "web", "digital",
        "design", "formation", "sante", "médecin", "medecin", "avocat", "comptab",
        "ingénieur", "ingenieur", "transport", "كراء", "location",
    ),
    "profession_liberale": (
        "avocat", "notaire", "medecin", "médecin", "expert", "comptab", "huissier",
        "architecte", "ingenieur", "conseil", "consult", "محامي", "طبيب", "خبير",
    ),
    "association": ("association", "جمعية", "ong", "fondation", "مؤسسة خيرية"),
    "licence": ("licence", "debit de boisson", "jeux", "قمار", "ترخيص", "ملهى", "spectacle"),
}

_DOMAIN_PRIORITY = (
    "hotellerie",
    "alcool",
    "tabac",
    "ciment",
    "tourisme",
    "agri",
    "profession_liberale",
    "services",
    "industrie",
    "commerce",
    "association",
)


def _blob(profile: TaxpayerProfile) -> str:
    parts = [
        profile.activity,
        profile.name,
        profile.commercial_name,
        profile.legal_form,
    ]
    return _norm(" | ".join(p for p in parts if p))


def detect_domain(profile: TaxpayerProfile) -> str:
    """Domaine d'activité fin (alcool, ciment, tourisme…), sinon le secteur."""
    blob = _blob(profile)
    for domain in _DOMAIN_PRIORITY:
        if any(k in blob for k in _KW[domain]):
            return domain
    sector = profile.sector
    if isinstance(sector, Sector):
        return sector.value
    return str(sector or "autre")


@dataclass(frozen=True)
class TaxDef:
    key: str  # clé de case, telle qu'écrite dans le PDF (arabe)
    label_fr: str
    label_ar: str
    amount_field: str | None  # champ FormAmounts associé (None = pas de montant)
    applies: Callable[[TaxpayerProfile, str], bool]


def _has_employees(p: TaxpayerProfile) -> bool:
    return bool(p.has_employees)


# —— lignes de taxes de la déclaration mensuelle (ordre visuel du formulaire) ——
FORM_TAXES: list[TaxDef] = [
    TaxDef(
        "خصم_من_المورد",
        "Retenue à la source",
        "الخصم من المورد",
        "retenues_total",
        # Salaires, honoraires, loyers, commissions… versés à des tiers.
        lambda p, b: bool(p.does_withholding) or _has_employees(p),
    ),
    TaxDef(
        "الأداء_على_التكوين_المهني",
        "TFP — Taxe de formation professionnelle",
        "الأداء على التكوين المهني",
        "tfp_amount",
        lambda p, b: bool(p.subject_tfp) if p.subject_tfp is not None else _has_employees(p),
    ),
    TaxDef(
        "صندوق_النهوض_بالمسكن",
        "FOPROLOS — Fonds de promotion du logement",
        "صندوق النهوض بالمسكن",
        "foprolos_amount",
        lambda p, b: (
            bool(p.subject_foprolos)
            if p.subject_foprolos is not None
            else _has_employees(p) and not p.totalement_exportatrice
        ),
    ),
    TaxDef(
        "المعلوم_على_الاستهلاك",
        "Droit de consommation (alcool, tabac, ciment…)",
        "المعلوم على الاستهلاك",
        None,
        lambda p, b: any(k in b for k in (_KW["alcool"] + _KW["tabac"] + _KW["ciment"])),
    ),
    TaxDef(
        "الأداء_على_القيمة_المضافة",
        "TVA — Taxe sur la valeur ajoutée",
        "الأداء على القيمة المضافة",
        "tva_collectee",
        lambda p, b: bool(p.subject_to_vat),
    ),
    TaxDef(
        "معاليم_أخرى_على_رقم_المعاملات",
        "Autres taxes sur CA (fonds tourisme, fonds compensation agricole…)",
        "معاليم أخرى على رقم المعاملات",
        None,
        # Fonds de promotion touristique, compensation agricole, etc.
        lambda p, b: (
            any(k in b for k in _KW["tourisme"] + _KW["hotellerie"])
            or (isinstance(p.sector, Sector) and p.sector == Sector.agriculture)
        ),
    ),
    TaxDef(
        "معلوم_الطابع_الجبائي",
        "Droit de timbre",
        "معلوم الطابع الجبائي",
        "stamp_duty_total",
        # 1 DT par facture encaissée : ne s'applique qu'aux activités facturant.
        lambda p, b: True,
    ),
    TaxDef(
        "المعلوم_على_المؤسسات",
        "Taxe sur les établissements à caractère industriel/commercial",
        "المعلوم على المؤسسات",
        "etablissement_tax_amount",
        lambda p, b: (
            bool(p.subject_etablissement)
            if p.subject_etablissement is not None
            else (
                isinstance(p.sector, Sector)
                and p.sector
                in {
                    Sector.commerce,
                    Sector.industrie,
                    Sector.services,
                    Sector.hotellerie,
                }
            )
        ),
    ),
    TaxDef(
        "المعلوم_على_النزل",
        "Taxe hôtelière",
        "المعلوم على النزل",
        "hotel_tax_amount",
        lambda p, b: (
            bool(p.subject_hotel_tax)
            if p.subject_hotel_tax is not None
            else any(k in b for k in _KW["hotellerie"])
        ),
    ),
    TaxDef(
        "معلوم_الإجازة",
        "Droit de licence (débits de boissons…)",
        "معلوم الإجازة",
        None,
        lambda p, b: bool(p.subject_licence) or any(k in b for k in _KW["licence"]),
    ),
]


@dataclass
class TaxAssessment:
    key: str
    label_fr: str
    label_ar: str
    amount_field: str | None
    applicable: bool
    domain: str
    reason: str

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label_fr": self.label_fr,
            "label_ar": self.label_ar,
            "amount_field": self.amount_field,
            "applicable": self.applicable,
            "mark": "X" if self.applicable else "X (sans objet)",
            "reason": self.reason,
        }


def assess_taxes(profile: TaxpayerProfile) -> dict[str, TaxAssessment]:
    """Évalue chaque ligne de taxe du formulaire selon le domaine d'activité."""
    blob = _blob(profile)
    domain = detect_domain(profile)
    out: dict[str, TaxAssessment] = {}
    for t in FORM_TAXES:
        try:
            applicable = bool(t.applies(profile, blob))
        except Exception:
            applicable = False
        reason = (
            "Applicable selon l'activité / les réponses."
            if applicable
            else "Sans objet pour ce domaine d'activité."
        )
        out[t.key] = TaxAssessment(
            key=t.key,
            label_fr=t.label_fr,
            label_ar=t.label_ar,
            amount_field=t.amount_field,
            applicable=applicable,
            domain=domain,
            reason=reason,
        )
    return out


def checkboxes_from(assessment: dict[str, TaxAssessment]) -> dict[str, bool]:
    return {key: a.applicable for key, a in assessment.items()}


def sans_objet_labels(assessment: dict[str, TaxAssessment]) -> list[str]:
    return [a.label_fr for a in assessment.values() if not a.applicable]


# —— correspondance secteur → domaine pour les questions de cadrage ——
SECTOR_QUESTION = {
    "id": "sector",
    "field": "sector",
    "type": "select",
    "question_fr": "Quel est votre domaine d'activité ?",
    "question_ar": "ما هو مجال نشاطك؟",
    "options": [
        {"value": "hotellerie", "label": "Hôtellerie / tourisme"},
        {"value": "agriculture", "label": "Agriculture / pêche"},
        {"value": "industrie", "label": "Industrie / fabrication"},
        {"value": "commerce", "label": "Commerce / distribution"},
        {"value": "services", "label": "Services / conseil / informatique"},
        {"value": "profession_liberale", "label": "Profession libérale"},
        {"value": "association", "label": "Association"},
        {"value": "autre", "label": "Autre"},
    ],
}
