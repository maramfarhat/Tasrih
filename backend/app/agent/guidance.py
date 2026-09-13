"""Guides pas-à-pas (français / arabe) — le script que l'avatar « dit ».

Fonctionne même sans IA : fournit le message proactif, des suggestions de questions
et l'élément d'interface à mettre en évidence pour chaque étape.

Le texte est produit directement dans la langue demandée (`lang="ar"` → arabe
standard / فصحى), afin que la synthèse vocale soit 100 % arabe (pas de mélange
français-arabe).
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
    7: "Retenue à la source (TEJ)",
    8: "Vérification des documents",
}

STEP_LABELS_AR: dict[int, str] = {
    0: "الرئيسية / الدخول",
    1: "الأسئلة",
    2: "وثائق الأعوان",
    3: "مسح الوثائق الجبائية",
    4: "ملف المؤسسة",
    5: "فواتير فاطورة",
    6: "استمارة التصريح",
    7: "الخصم من المورد (TEJ)",
    8: "التحقق من الوثائق",
}


def _pick(lang: str, fr: str, ar: str) -> str:
    return ar if lang == "ar" else fr


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


def guidance_for(
    step: int | None,
    context: dict[str, Any] | None = None,
    lang: str = "fr",
) -> dict[str, Any]:
    """Retourne {message, suggestions, highlight, step_label} pour l'étape donnée."""
    context = context or {}
    step = step if step is not None else 0
    profile = context.get("profile") or {}
    cif = context.get("cif") or {}
    rne = context.get("rne") or {}
    invoices = context.get("invoices") or []
    needs = context.get("needs_user_review") or []
    ar = lang == "ar"

    name = _first(profile, "name") or _first(cif, "name") or _first(rne, "company_name")
    who = f" {name}" if name else ""

    message = ""
    highlight = None

    if step <= 0:
        if context.get("logged_in"):
            message = _pick(
                lang,
                "Vous êtes sur votre accueil Tasrih. Commencez ou reprenez votre "
                "déclaration, ou scannez vos documents. Dites-moi si vous avez besoin d'aide.",
                "أنت في الصفحة الرئيسية لتصريح. ابدأ تصريحك أو تابع ما بدأته، أو امسح وثائقك. "
                "أخبرني إن احتجت إلى مساعدة.",
            )
            highlight = "home"
        else:
            message = _pick(
                lang,
                "Bonjour, je suis Karim, votre assistant Tasrih. Créez votre compte ou "
                "connectez-vous, et je vous guiderai pas à pas pour préparer votre "
                "déclaration mensuelle.",
                "مرحبًا، أنا كريم، مساعدك في منصة تصريح. أنشئ حسابك أو سجّل الدخول، "
                "وسأرافقك خطوة بخطوة لإعداد تصريحك الشهري.",
            )
            highlight = "auth"
    elif step == 1:
        idx = context.get("q_index")
        if idx == 1:
            message = _pick(
                lang,
                "Indiquez si vous avez du personnel. Si oui, vous devrez déposer "
                "le contrat de travail, la fiche CNSS et la fiche de paie de chaque employé.",
                "حدّد إن كان لديك أعوان. إذا نعم، ستودع عقد العمل وبطاقة الضمان الاجتماعي "
                "وبطاقة الأجر لكل عون.",
            )
        elif idx == 2:
            message = _pick(
                lang,
                "Choisissez comment vous déposez habituellement vos déclarations. "
                "Cela m'aide à personnaliser votre parcours.",
                "اختر الطريقة التي تُودع بها تصريحاتك عادةً. يساعدني ذلك على تخصيص مسارك.",
            )
        elif idx == 3:
            message = _pick(
                lang,
                "Dernière question : un expert-comptable gère-t-il votre paie ou vos "
                "déclarations ? Répondez, puis nous passons aux documents.",
                "السؤال الأخير: هل يدير خبير محاسب أجورك أو تصريحاتك؟ أجب ثم ننتقل إلى الوثائق.",
            )
        else:
            message = _pick(
                lang,
                "Pour commencer, indiquez votre IS de l'année précédente : le montant ou "
                "la référence de votre impôt sur les sociétés.",
                "للبدء، أدخل الضريبة على الشركات للسنة الفارطة: المبلغ أو مرجع الضريبة.",
            )
        highlight = "question"
    elif step == 2:
        n = _count(context.get("employees"))
        if n:
            message = _pick(
                lang,
                f"{n} employé{'s' if n > 1 else ''} enregistré{'s' if n > 1 else ''}. "
                "Pour chaque employé, déposez le contrat de travail, la fiche CNSS et "
                "la fiche de paie. Vous pouvez en ajouter d'autres.",
                f"تم تسجيل {n} عونًا. لكل عون، أودع عقد العمل وبطاقة الضمان الاجتماعي "
                "وبطاقة الأجر. يمكنك إضافة المزيد.",
            )
        else:
            message = _pick(
                lang,
                "Pour chaque employé, déposez le contrat de travail, la fiche CNSS et "
                "la fiche de paie. Vous pouvez ajouter plusieurs employés, l'un après l'autre.",
                "لكل عون، أودع عقد العمل وبطاقة الضمان الاجتماعي وبطاقة الأجر. "
                "يمكنك إضافة عدة أعوان، واحدًا بعد الآخر.",
            )
        highlight = "employees"
    elif step == 3:
        has_cif = bool(_first(cif, "tax_id") or _first(cif, "name"))
        has_rne = bool(_first(rne, "rne_identifier") or _first(rne, "company_name"))
        if has_cif and not has_rne:
            message = _pick(
                lang,
                f"Très bien{who}, j'ai lu la carte fiscale. Téléversez maintenant "
                "l'extrait RNE pour compléter la forme juridique.",
                f"حسنًا{who}، قرأت البطاقة الجبائية. حمّل الآن مضمون السجل الوطني "
                "لإكمال الشكل القانوني.",
            )
        elif has_rne and not has_cif:
            message = _pick(
                lang,
                "J'ai l'extrait RNE. Il me manque la carte d'identification fiscale : "
                "téléversez-la pour récupérer le matricule fiscal.",
                "لديّ مضمون السجل الوطني. ينقصني التعريف الجبائي: حمّله لاستخراج المعرّف الجبائي.",
            )
        elif has_cif and has_rne:
            message = _pick(
                lang,
                "Parfait, les deux documents sont lus. Vérifions ensemble le profil "
                "de l'entreprise avant de continuer.",
                "ممتاز، تمّت قراءة الوثيقتين. لنتحقق معًا من ملف المؤسسة قبل المتابعة.",
            )
        else:
            message = _pick(
                lang,
                "Téléversez d'abord votre carte d'identification fiscale, puis l'extrait "
                "RNE. Utilisez une image nette : je lis le matricule et l'activité.",
                "حمّل أولًا التعريف الجبائي ثم مضمون السجل الوطني. استعمل صورة واضحة: "
                "أقرأ المعرّف والنشاط.",
            )
        highlight = "scan"
    elif step == 4:
        message = _pick(
            lang,
            "Vérifiez le profil extrait, surtout le matricule fiscal et la forme juridique. "
            "Corrigez directement si une valeur est fausse, puis validez le mois et l'année.",
            "تحقّق من الملف المستخرج، خاصة المعرّف الجبائي والشكل القانوني. صحّح مباشرة "
            "إن كانت قيمة خاطئة، ثم أكّد الشهر والسنة.",
        )
        highlight = "profile"
    elif step == 5:
        n = _count(invoices)
        if n == 0:
            message = _pick(
                lang,
                "Importez vos factures électroniques au format XML TEIF, exportées depuis "
                "El Fatoora. Je calcule automatiquement la TVA, le timbre et le chiffre d'affaires.",
                "استورد فواتيرك الإلكترونية بصيغة XML TEIF المُصدَّرة من فاطورة. "
                "أحسب تلقائيًا الأداء على القيمة المضافة والطابع ورقم المعاملات.",
            )
        else:
            message = _pick(
                lang,
                f"J'ai bien reçu {n} facture{'s' if n > 1 else ''}. "
                "Quand tout est là, lancez le calcul pour remplir la déclaration mensuelle.",
                f"تلقّيت {n} فاتورة. عندما يكتمل كل شيء، شغّل الحساب لتعبئة التصريح الشهري.",
            )
        highlight = "invoices"
    elif step == 7:
        message = _pick(
            lang,
            "Étape retenue à la source : si vous avez payé des montants soumis à retenue, "
            "exportez le fichier XML depuis le portail TEJ (tej.finances.gov.tn) puis "
            "importez-le ici. Je remplis le tableau officiel « Retenue à la source ». "
            "Sinon, continuez directement vers la déclaration mensuelle.",
            "مرحلة الخصم من المورد: إن دفعت مبالغ خاضعة للخصم، صدّر ملف XML من بوابة TEJ "
            "ثم استورده هنا. أعبّئ الجدول الرسمي «الخصم من المورد». وإلا، تابع مباشرة "
            "إلى التصريح الشهري.",
        )
        highlight = "tej"
    elif step == 8:
        message = _pick(
            lang,
            "Vérifiez les informations extraites de la carte fiscale et de l'extrait RNE. "
            "Corrigez ou rescannez les champs marqués « Non extrait » avant de continuer.",
            "تحقّق من المعلومات المستخرجة من بطاقة التعريف الجبائي ومضمون السجل الوطني. "
            "صحّح أو أعد مسح الحقول المعلّمة «لم يُستخرج» قبل المتابعة.",
        )
        highlight = "verify"
    elif step == 6:
        if needs:
            first = str(needs[0])
            message = _pick(
                lang,
                "La déclaration est prête, mais vérifiez ce point : "
                f"{first} Répondez à la question sur les retenues, puis ouvrez le formulaire officiel.",
                "التصريح جاهز، لكن تحقّق من هذه النقطة: "
                f"{first} أجب عن سؤال الخصم من المورد ثم افتح الاستمارة الرسمية.",
            )
        else:
            message = _pick(
                lang,
                "La déclaration est prête. Vérifiez les montants affichés, puis ouvrez le "
                "formulaire officiel prérempli. Relisez toujours avant le dépôt.",
                "التصريح جاهز. تحقّق من المبالغ المعروضة ثم افتح الاستمارة الرسمية المعبأة "
                "مسبقًا. راجع دائمًا قبل الإيداع.",
            )
        highlight = "form"
    else:
        message = _pick(
            lang,
            "Je suis là pour vous guider. Dites-moi où vous bloquez.",
            "أنا هنا لإرشادك. أخبرني أين تواجه صعوبة.",
        )

    return {
        "step": step,
        "step_label": (STEP_LABELS_AR if ar else STEP_LABELS).get(step, ""),
        "message": message,
        "suggestions": suggestions_for(step, context, lang),
        "highlight": highlight,
    }


def suggestions_for(
    step: int | None,
    context: dict[str, Any] | None = None,
    lang: str = "fr",
) -> list[str]:
    context = context or {}
    if step is None:
        step = 0
    ar = lang == "ar"
    if step <= 0:
        return (
            ["كيف أنشئ حسابًا؟", "ما فائدة تصريح؟", "هل الخدمة مجانية؟"]
            if ar
            else ["Comment créer un compte ?", "À quoi sert Tasrih ?", "Est-ce gratuit ?"]
        )
    if step == 1:
        return (
            ["ما هي الضريبة على الشركات؟", "أين أجد ضريبتي؟", "لماذا هذه الأسئلة؟"]
            if ar
            else ["C'est quoi l'IS ?", "Où trouver mon IS ?", "Pourquoi ces questions ?"]
        )
    if step == 2:
        return (
            ["أين أجد بطاقة الضمان الاجتماعي؟", "أين أجد بطاقة الأجر؟", "الصيغ المقبولة؟"]
            if ar
            else ["Où trouver la fiche CNSS ?", "Où trouver la fiche de paie ?", "Formats acceptés ?"]
        )
    if step == 3:
        return (
            ["أين أجد معرّفي الجبائي؟", "أين أجد مضمون السجل الوطني؟", "لماذا لا تُقرأ وثيقتي؟"]
            if ar
            else [
                "Où trouver mon matricule fiscal ?",
                "Où trouver l'extrait RNE ?",
                "Mon scan n'est pas lu ?",
            ]
        )
    if step == 4:
        return (
            ["ما هو شكلي القانوني؟", "ما هو رمز الأداء على القيمة المضافة؟", "هل يجب التحقق من كل شيء؟"]
            if ar
            else ["Quelle est ma forme juridique ?", "Qu'est-ce que le code TVA ?", "Dois-je tout vérifier ?"]
        )
    if step == 5:
        return (
            ["من أين أصدّر فواتير فاطورة؟", "لماذا XML فقط؟", "وماذا لو كانت لدي مشتريات؟"]
            if ar
            else [
                "Où exporter mes factures Fatoora ?",
                "Pourquoi uniquement du XML ?",
                "Et si j'ai un achat ?",
            ]
        )
    if step == 7:
        return (
            ["أين أجد XML في TEJ؟", "ما هو الخصم من المورد؟", "هل يمكنني تخطي هذه المرحلة؟"]
            if ar
            else [
                "Où trouver le XML sur TEJ ?",
                "C'est quoi la retenue à la source ?",
                "Puis-je passer cette étape ?",
            ]
        )
    return (
        ["كيف أتحقق من المبالغ؟", "ما هو الطابع الجبائي؟", "هل يمكنني إيداع هذا الملف؟"]
        if ar
        else ["Comment vérifier les montants ?", "C'est quoi le timbre ?", "Puis-je déposer ce PDF ?"]
    )
