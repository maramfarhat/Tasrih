"""Guides pas-à-pas (français) — le script par défaut que l'avatar « dit ».

Fonctionne même sans IA : fournit le message proactif, des suggestions de questions
et l'élément d'interface à mettre en évidence pour chaque étape.
"""

from __future__ import annotations

from typing import Any

STEP_LABELS: dict[int, str] = {
    0: "Accueil / Connexion",
    1: "Questions",
    2: "Documents du personnel",
    3: "Scan des documents fiscaux",
    4: "Profil entreprise",
    5: "Factures Fatoora",
    6: "Formulaire de déclaration",
}


def _first(value: Any, *keys: str) -> str:
    if not isinstance(value, dict):
        return ""
    for key in keys:
        v = value.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    return 0


def guidance_for(step: int | None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Retourne {message, suggestions, highlight, step_label} pour l'étape donnée."""
    context = context or {}
    step = step if step is not None else 0
    profile = context.get("profile") or {}
    cif = context.get("cif") or {}
    rne = context.get("rne") or {}
    onboarding = context.get("onboarding") or {}
    invoices = context.get("invoices") or []
    needs = context.get("needs_user_review") or []

    name = _first(profile, "name") or _first(cif, "name") or _first(rne, "company_name")
    who = f" {name}" if name else ""

    message = ""
    highlight = None

    if step <= 0:
        if context.get("logged_in"):
            message = (
                "Bonjour, je suis Karim, votre assistant Tasrih. Vous êtes sur votre "
                "accueil : commencez ou reprenez votre déclaration, ou scannez vos "
                "documents. Dites-moi si vous avez besoin d'aide."
            )
            highlight = "home"
        else:
            message = (
                "Bonjour, je suis Karim, votre assistant Tasrih. "
                "Créez votre compte ou connectez-vous, et je vous guiderai pas à pas "
                "pour préparer votre déclaration mensuelle."
            )
            highlight = "auth"
    elif step == 1:
        idx = context.get("q_index")
        if idx == 1:
            message = (
                "Indiquez si vous avez du personnel. Si oui, vous devrez déposer "
                "le contrat de travail et la fiche CNSS de chaque employé."
            )
        elif idx == 2:
            message = (
                "Choisissez comment vous déposez habituellement vos déclarations. "
                "Cela m'aide à personnaliser votre parcours."
            )
        elif idx == 3:
            message = (
                "Dernière question : un expert-comptable gère-t-il votre paie ou vos "
                "déclarations ? Répondez, puis nous passons aux documents."
            )
        else:
            message = (
                "Commençons. Indiquez votre IS de l'année précédente : le montant ou "
                "la référence de votre impôt sur les sociétés."
            )
        highlight = "question"
    elif step == 2:
        message = (
            "Pour chaque employé, déposez le contrat de travail et la fiche CNSS. "
            "Vous pouvez ajouter plusieurs employés, l'un après l'autre."
        )
        highlight = "employees"
    elif step == 3:
        has_cif = bool(_first(cif, "tax_id") or _first(cif, "name"))
        has_rne = bool(_first(rne, "rne_identifier") or _first(rne, "company_name"))
        if has_cif and not has_rne:
            message = (
                f"Très bien{who}, j'ai lu la carte fiscale. "
                "Téléversez maintenant l'extrait RNE pour compléter la forme juridique."
            )
        elif has_rne and not has_cif:
            message = (
                "J'ai l'extrait RNE. Il me manque la carte d'identification fiscale : "
                "téléversez-la pour récupérer le matricule fiscal."
            )
        elif has_cif and has_rne:
            message = (
                "Parfait, les deux documents sont lus. Vérifions ensemble le profil "
                "de l'entreprise avant de continuer."
            )
        else:
            message = (
                "Téléversez d'abord votre carte d'identification fiscale, puis l'extrait "
                "RNE. Utilisez une image nette : je lis le matricule et l'activité."
            )
        highlight = "scan"
    elif step == 4:
        message = (
            "Vérifiez le profil extrait, surtout le matricule fiscal et la forme juridique. "
            "Corrigez directement si une valeur est fausse, puis validez le mois et l'année."
        )
        highlight = "profile"
    elif step == 5:
        n = _count(invoices)
        if n == 0:
            message = (
                "Importez vos factures électroniques au format XML TEIF, exportées depuis "
                "El Fatoora. Je calcule automatiquement la TVA, le timbre et le chiffre d'affaires."
            )
        else:
            message = (
                f"J'ai bien reçu {n} facture{'s' if n > 1 else ''}. "
                "Quand tout est là, lancez le calcul pour remplir la déclaration mensuelle."
            )
        highlight = "invoices"
    elif step >= 6:
        if needs:
            first = str(needs[0])
            message = (
                "La déclaration est prête, mais vérifiez ce point : "
                f"{first} Répondez à la question sur les retenues, puis ouvrez le formulaire officiel."
            )
        else:
            message = (
                "La déclaration est prête. Vérifiez les montants affichés, puis ouvrez le "
                "formulaire officiel prérempli. Relisez toujours avant le dépôt."
            )
        highlight = "form"
    else:
        message = "Je suis là pour vous guider. Dites-moi où vous bloquez."

    return {
        "step": step,
        "step_label": STEP_LABELS.get(step, ""),
        "message": message,
        "suggestions": suggestions_for(step, context),
        "highlight": highlight,
    }


def suggestions_for(step: int | None, context: dict[str, Any] | None = None) -> list[str]:
    context = context or {}
    if step is None:
        step = 0
    if step <= 0:
        return ["Comment créer un compte ?", "À quoi sert Tasrih ?", "Est-ce gratuit ?"]
    if step == 1:
        return ["C'est quoi l'IS ?", "Où trouver mon IS ?", "Pourquoi ces questions ?"]
    if step == 2:
        return ["Où trouver la fiche CNSS ?", "Si je n'ai pas de salariés ?", "Formats acceptés ?"]
    if step == 3:
        return ["Où trouver mon matricule fiscal ?", "Où trouver l'extrait RNE ?", "Mon scan n'est pas lu ?"]
    if step == 4:
        return ["Quelle est ma forme juridique ?", "Qu'est-ce que le code TVA ?", "Dois-je tout vérifier ?"]
    if step == 5:
        return ["Où exporter mes factures Fatoora ?", "Pourquoi uniquement du XML ?", "Et si j'ai un achat ?"]
    return ["Comment vérifier les montants ?", "C'est quoi le timbre ?", "Puis-je déposer ce PDF ?"]
