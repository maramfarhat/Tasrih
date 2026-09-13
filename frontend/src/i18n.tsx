/**
 * Internationalisation FR ⇄ AR.
 *
 * Deux mécanismes complémentaires :
 *  1. `t(clé)` — traduction explicite des chaînes statiques (landing, chrome…).
 *  2. `PHRASES` + traducteur DOM — couche globale qui remplace les phrases
 *     françaises restantes (y compris les messages venant du backend, ex. Karim)
 *     par leur version arabe. Cela garantit que l'interface ne contient plus de
 *     français en mode arabe.
 *
 * `setLang` met à jour <html lang> et <html dir> (RTL/LTR) et persiste le choix.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export type Lang = 'fr' | 'ar'
export type Dir = 'ltr' | 'rtl'

type Entry = { fr: string; ar: string }

/** Dictionnaire des chaînes traduites explicitement (clé = texte source). */
export const DICT: Record<string, Entry> = {
  // ——— Chrome / navigation ———
  'Se connecter': { fr: 'Se connecter', ar: 'تسجيل الدخول' },
  "S'inscrire": { fr: "S'inscrire", ar: 'إنشاء حساب' },
  'Sign up': { fr: "S'inscrire", ar: 'إنشاء حساب' },
  'Sign in': { fr: 'Se connecter', ar: 'تسجيل الدخول' },
  Connexion: { fr: 'Connexion', ar: 'تسجيل الدخول' },
  Déconnexion: { fr: 'Déconnexion', ar: 'تسجيل الخروج' },
  Accueil: { fr: 'Accueil', ar: 'الرئيسية' },
  'Chargement…': { fr: 'Chargement…', ar: 'جارٍ التحميل…' },
  'Créer un compte': { fr: 'Créer un compte', ar: 'إنشاء حساب' },
  'Créer mon compte': { fr: 'Créer mon compte', ar: 'إنشاء حسابي' },
  Email: { fr: 'Email', ar: 'البريد الإلكتروني' },
  'Mot de passe': { fr: 'Mot de passe', ar: 'كلمة المرور' },
  'Numéro de téléphone': { fr: 'Numéro de téléphone', ar: 'رقم الهاتف' },
  'Patientez…': { fr: 'Patientez…', ar: 'يرجى الانتظار…' },
  "S'inscrire et continuer": { fr: "S'inscrire et continuer", ar: 'إنشاء الحساب والمتابعة' },
  'Accédez à votre espace pour préparer votre déclaration mensuelle.': {
    fr: 'Accédez à votre espace pour préparer votre déclaration mensuelle.',
    ar: 'ادخل إلى فضائك لإعداد تصريحك الشهري.',
  },

  // ——— Étapes (barre de progression) ———
  Documents: { fr: 'Documents', ar: 'الوثائق' },
  Questions: { fr: 'Questions', ar: 'الأسئلة' },
  Personnel: { fr: 'Personnel', ar: 'الأعوان' },
  Profil: { fr: 'Profil', ar: 'الملف' },
  Factures: { fr: 'Factures', ar: 'الفواتير' },
  'Retenue TEJ': { fr: 'Retenue TEJ', ar: 'الخصم من المورد' },
  Formulaire: { fr: 'Formulaire', ar: 'الاستمارة' },

  // ——— Landing : héros ———
  Tasrih: { fr: 'Tasrih', ar: 'تصريح' },
  'Plateforme d’aide à la déclaration mensuelle tunisienne : documents fiscaux, factures électroniques Fatoora et formulaire officiel prérempli.':
    {
      fr: 'Plateforme d’aide à la déclaration mensuelle tunisienne : documents fiscaux, factures électroniques Fatoora et formulaire officiel prérempli.',
      ar: 'منصة لمساعدة المؤسسات التونسية على إعداد التصريح الشهري: وثائق جبائية، فواتير إلكترونية (فاطورة) واستمارة رسمية معبأة مسبقًا.',
    },
  'Votre déclaration en 5 étapes': {
    fr: 'Votre déclaration en 5 étapes',
    ar: 'تصريحك في ٥ خطوات',
  },
  'Un parcours simple et guidé': { fr: 'Un parcours simple et guidé', ar: 'مسار بسيط وموجَّه' },

  // ——— Landing : cartes d'étapes ———
  'Documents fiscaux': { fr: 'Documents fiscaux', ar: 'الوثائق الجبائية' },
  'Carte d’identification fiscale et extrait RNE lus automatiquement (OCR).': {
    fr: 'Carte d’identification fiscale et extrait RNE lus automatiquement (OCR).',
    ar: 'تُقرأ بطاقة التعريف الجبائي ومضمون السجل الوطني للمؤسسات تلقائيًا.',
  },
  'IS, personnel et canal de dépôt : quelques questions pour cadrer votre déclaration.':
    {
      fr: 'IS, personnel et canal de dépôt : quelques questions pour cadrer votre déclaration.',
      ar: 'الضريبة على الشركات، الأعوان وقناة الإيداع: بعض الأسئلة لتأطير تصريحك.',
    },
  'Factures Fatoora': { fr: 'Factures Fatoora', ar: 'فواتير فاطورة' },
  'Importez vos factures électroniques TEIF (XML) et calculez la TVA.': {
    fr: 'Importez vos factures électroniques TEIF (XML) et calculez la TVA.',
    ar: 'استورد فواتيرك الإلكترونية TEIF (XML) واحسب الأداء على القيمة المضافة.',
  },
  'Retenue à la source (TEJ)': { fr: 'Retenue à la source (TEJ)', ar: 'الخصم من المورد (TEJ)' },
  'Exportez le XML sur <strong>tej.finances.gov.tn</strong> puis générez le tableau officiel « Retenue à la source ».':
    {
      fr: 'Exportez le XML sur tej.finances.gov.tn puis générez le tableau officiel « Retenue à la source ».',
      ar: 'صدّر ملف XML من tej.finances.gov.tn ثم أنشئ الجدول الرسمي «الخصم من المورد».',
    },
  'Formulaire officiel': { fr: 'Formulaire officiel', ar: 'الاستمارة الرسمية' },
  'Générez la déclaration mensuelle préremplie et exportez le PDF officiel.': {
    fr: 'Générez la déclaration mensuelle préremplie et exportez le PDF officiel.',
    ar: 'أنشئ التصريح الشهري المعبأ مسبقًا وصدّر ملف PDF الرسمي.',
  },

  // ——— Landing : FAQ ———
  'Questions Fréquemment Posées': { fr: 'Questions Fréquemment Posées', ar: 'الأسئلة الشائعة' },
  'Trouvez rapidement les réponses à vos questions': {
    fr: 'Trouvez rapidement les réponses à vos questions',
    ar: 'اعثر بسرعة على أجوبة لأسئلتك',
  },
  'Quels documents faut-il fournir ?': {
    fr: 'Quels documents faut-il fournir ?',
    ar: 'ما هي الوثائق المطلوبة؟',
  },
  'Comment mes documents sont-ils lus ?': {
    fr: 'Comment mes documents sont-ils lus ?',
    ar: 'كيف تُقرأ وثائقي؟',
  },
  'Quelles factures puis-je importer ?': {
    fr: 'Quelles factures puis-je importer ?',
    ar: 'ما هي الفواتير التي يمكنني استيرادها؟',
  },
  'Le PDF généré est-il le formulaire officiel ?': {
    fr: 'Le PDF généré est-il le formulaire officiel ?',
    ar: 'هل ملف PDF الناتج هو الاستمارة الرسمية؟',
  },
  'La carte d’identification fiscale et l’extrait RNE de votre entreprise, puis vos factures électroniques du mois. Aucun justificatif papier n’est requis.':
    {
      fr: 'La carte d’identification fiscale et l’extrait RNE de votre entreprise, puis vos factures électroniques du mois. Aucun justificatif papier n’est requis.',
      ar: 'بطاقة التعريف الجبائي ومضمون السجل الوطني للمؤسسات، ثم فواتيرك الإلكترونية لهذا الشهر. لا تُطلب أي وثيقة ورقية.',
    },
  'Les informations (matricule fiscal, code TVA, code catégorie, forme juridique…) sont extraites automatiquement par OCR puis vérifiées. Vous pouvez corriger chaque champ avant de continuer.':
    {
      fr: 'Les informations (matricule fiscal, code TVA, code catégorie, forme juridique…) sont extraites automatiquement par OCR puis vérifiées. Vous pouvez corriger chaque champ avant de continuer.',
      ar: 'تُستخرج المعلومات (المعرّف الجبائي، رمز الأداء على القيمة المضافة، رمز الصنف، الشكل القانوني…) تلقائيًا ثم تُتحقّق. يمكنك تصحيح كل حقل قبل المتابعة.',
    },
  'Les factures électroniques au format TEIF / Fatoora (fichiers XML) émises et reçues. La TVA collectée et déductible est calculée automatiquement.':
    {
      fr: 'Les factures électroniques au format TEIF / Fatoora (fichiers XML) émises et reçues. La TVA collectée et déductible est calculée automatiquement.',
      ar: 'الفواتير الإلكترونية بصيغة TEIF / فاطورة (ملفات XML) الصادرة والواردة. يُحسب الأداء على القيمة المضافة المستوجب والقابل للخصم تلقائيًا.',
    },
  'Oui, la déclaration reprend le formulaire officiel mensuelle2026 (12 pages), prérempli et modifiable. Vérifiez toujours les montants avant le dépôt.':
    {
      fr: 'Oui, la déclaration reprend le formulaire officiel mensuelle2026 (12 pages), prérempli et modifiable. Vérifiez toujours les montants avant le dépôt.',
      ar: 'نعم، يعتمد التصريح على الاستمارة الرسمية mensuelle2026 (12 صفحة)، معبأة مسبقًا وقابلة للتعديل. تحقّق دائمًا من المبالغ قبل الإيداع.',
    },

  // ——— Pied de page ———
  'Tasrih — Déclaration mensuelle Tunisie © 2026': {
    fr: 'Tasrih — Déclaration mensuelle Tunisie © 2026',
    ar: 'تصريح — التصريح الشهري بتونس © 2026',
  },
  'Informations légales': { fr: 'Informations légales', ar: 'معلومات قانونية' },
  'Protection des données': { fr: 'Protection des données', ar: 'حماية المعطيات' },
  'Conditions Générales': { fr: 'Conditions Générales', ar: 'الشروط العامة' },

  // ——— Assistant ———
  'assistant Tasrih': { fr: 'assistant Tasrih', ar: 'مساعد تصريح' },
  'parle…': { fr: 'parle…', ar: 'يتحدّث…' },
  'réfléchit…': { fr: 'réfléchit…', ar: 'يفكّر…' },
  'Karim écrit…': { fr: 'Karim écrit…', ar: 'كريم يكتب…' },
  'Posez votre question…': { fr: 'Posez votre question…', ar: 'اطرح سؤالك…' },
  'Ouvrir l’assistant': { fr: 'Ouvrir l’assistant', ar: 'فتح المساعد' },
  "Fermer l'assistant": { fr: "Fermer l'assistant", ar: 'إغلاق المساعد' },
  'Couper la voix': { fr: 'Couper la voix', ar: 'كتم الصوت' },
  'Réactiver la voix': { fr: 'Réactiver la voix', ar: 'تشغيل الصوت' },
  'Effacer la conversation': { fr: 'Effacer la conversation', ar: 'مسح المحادثة' },
  'Activez la voix': { fr: 'Activez la voix', ar: 'فعّل الصوت' },
  Fermer: { fr: 'Fermer', ar: 'إغلاق' },
}

/**
 * Phrase → arabe. Alimente le traducteur global (texte du DOM et messages
 * backend). Les clés sont remplacées des plus longues aux plus courtes.
 */
export const EXTRA_PHRASES: Record<string, string> = {
  // ——— Actions / boutons ———
  Continuer: 'متابعة',
  Retour: 'رجوع',
  'Retour factures': 'رجوع إلى الفواتير',
  'Retour profil': 'رجوع إلى الملف',
  'Retour retenue (TEJ)': 'رجوع إلى الخصم من المورد',
  Vider: 'تفريغ',
  'Ajouter cet employé': 'إضافة هذا العون',
  'Appliquer et recalculer': 'تطبيق وإعادة الحساب',
  'Annuler mes modifications': 'إلغاء تعديلاتي',
  'Réouvrir la déclaration mensuelle': 'إعادة فتح التصريح الشهري',
  'Générer le PDF « Retenue à la source »': 'إنشاء ملف PDF «الخصم من المورد»',
  'Remplir la déclaration mensuelle': 'تعبئة التصريح الشهري',
  'Calculer depuis les fiches de paie scannées': 'احسب من بطاقات الأجر الممسوحة',
  'Accéder aux factures (Fatoora)': 'الانتقال إلى الفواتير (فاطورة)',
  'Ouvrir tej.finances.gov.tn ↗': 'فتح tej.finances.gov.tn ↗',
  'Commencer maintenant': 'ابدأ الآن',
  'Démarrer ma déclaration': 'ابدأ تصريحي',
  'Sign up': 'إنشاء حساب',
  'Sign in': 'تسجيل الدخول',

  // ——— Questions ———
  'Question 1 / 4': 'السؤال 1 / 4',
  'Question 2 / 4': 'السؤال 2 / 4',
  'Question 3 / 4': 'السؤال 3 / 4',
  'Question 4 / 4': 'السؤال 4 / 4',
  'Quel est votre IS de l’année précédente ?': 'ما هي الضريبة على الشركات للسنة الفارطة؟',
  'Indiquez le montant ou la référence de votre impôt sur les sociétés.':
    'أدخل مبلغ أو مرجع الضريبة على الشركات.',
  'IS année précédente': 'الضريبة على الشركات للسنة الفارطة',
  'Montant ou référence IS': 'المبلغ أو مرجع الضريبة',
  'Avez-vous du personnel ?': 'هل لديك أعوان؟',
  'Si oui, vous déposerez le contrat de travail et la fiche CNSS pour chaque employé.':
    'إذا نعم، ستودع عقد العمل وبطاقة الأجر لكل عون.',
  'Comment déposez-vous vos déclarations ?': 'كيف تُودع تصريحاتك؟',
  'Choisissez votre canal habituel de dépôt.': 'اختر قناة الإيداع المعتادة.',
  'Cela aide à personnaliser les prochaines étapes.': 'يساعد ذلك على تخصيص المراحل القادمة.',
  'Un expert comptable gère-t-il votre paie / déclarations ?':
    'هل يدير خبير محاسب أجورك / تصريحاتك؟',
  'Oui': 'نعم',
  'Non': 'لا',
  'En ligne (portail fiscal)': 'عبر الإنترنت (بوابة الجباية)',
  'Dépôt papier': 'إيداع ورقي',
  'Via expert comptable': 'عبر خبير محاسب',
  'Autre': 'أخرى',

  // ——— Documents fiscaux ———
  'Documents fiscaux': 'الوثائق الجبائية',
  'Téléversez la carte d’identification fiscale et l’extrait RNE — un fichier à la fois.':
    'حمّل بطاقة التعريف الجبائي ومضمون السجل الوطني — ملف واحد في كل مرة.',
  'Carte d’identification fiscale': 'بطاقة التعريف الجبائي',
  'Carte fiscale chargée': 'تم تحميل البطاقة الجبائية',
  'Extrait RNE': 'مضمون السجل الوطني',
  'Extrait RNE chargé': 'تم تحميل مضمون السجل',
  'PDF ou photo': 'PDF أو صورة',
  'nom ?': 'الاسم؟',
  'matricule ?': 'المعرّف؟',
  'raison ?': 'الاسم الاجتماعي؟',
  'id ?': 'المعرّف؟',
  'Extraction vide — rescanner une image plus nette (OCR eng activé).':
    'الاستخراج فارغ — أعد مسح صورة أوضح.',

  // ——— Personnel ———
  'Documents du personnel': 'وثائق الأعوان',
  'Pour chaque employé, déposez le contrat de travail, la fiche CNSS et la fiche de paie.':
    'لكل عون، أودع عقد العمل وبطاقة الأجر.',
  'Nom de l’employé': 'اسم العون',
  'Contrat de travail': 'عقد العمل',
  'Fiche CNSS': 'بطاقة الضمان الاجتماعي',
  'Fiche de paie': 'بطاقة الأجر',
  'Zone statique — aucun dépôt': 'منطقة ثابتة — دون إيداع',
  'Nom de l’employé requis': 'اسم العون مطلوب',
  'Ajoutez le contrat de travail, la fiche CNSS et/ou la fiche de paie':
    'أضف عقد العمل وبطاقة الضمان الاجتماعي و/أو بطاقة الأجر',

  // ——— Profil ———
  'Profil entreprise': 'ملف المؤسسة',
  'Vérifiez les champs extraits — corrigez notamment la forme juridique si besoin.':
    'تحقّق من الحقول المستخرجة — صحّح لا سيما الشكل القانوني عند الحاجة.',
  'Raison sociale / Nom': 'الاسم الاجتماعي / الاسم',
  'Matricule fiscal': 'المعرّف الجبائي',
  'Code TVA': 'رمز الأداء على القيمة المضافة',
  'Code catégorie': 'رمز الصنف',
  'Identifiant RNE': 'معرّف السجل الوطني',
  'Nom commercial': 'الاسم التجاري',
  Adresse: 'العنوان',
  Activité: 'النشاط',
  'Forme juridique': 'الشكل القانوني',
  'Statut TVA (carte)': 'الوضعية الجبائية (البطاقة)',
  'Choisir (extrait RNE)…': 'اختر (من مضمون السجل الوطني)…',
  Mois: 'الشهر',
  Année: 'السنة',
  'SARL — Société à responsabilité limitée': 'شركة ذات مسؤولية محدودة',
  'SA — Société anonyme': 'شركة خفية الاسم',
  'SUARL — Société unipersonnelle à responsabilité limitée': 'شركة الشخص الواحد ذات مسؤولية محدودة',
  'SNC — Société en nom collectif': 'شركة التضامن',
  'SCS — Société en commandite simple': 'شركة التوصية البسيطة',
  'SCA — Société en commandite par actions': 'شركة التوصية بالأسهم',

  // ——— Factures ———
  'Fatoora — factures TEIF': 'فاطورة — فواتير TEIF',
  'Importez le fichier XML TEIF exporté depuis El Fatoora / TTN. Tasrih lit HT, TVA, TTC, timbre et lignes, puis remplit la déclaration mensuelle.':
    'استورد ملف XML TEIF المُصدَّر من فاطورة / TTN. يقرأ تصريح الجملة قبل الأداء، الأداء على القيمة المضافة، الجملة بكل الأداءات، الطابع والأسطر ثم يعبّئ التصريح الشهري.',
  'Déposer le fichier Fatoora (XML)': 'إيداع ملف فاطورة (XML)',
  'TEIF_FAC-….xml — un ou plusieurs fichiers': 'TEIF_FAC-….xml — ملف أو أكثر',
  'Lecture TEIF…': 'قراءة TEIF…',
  'TEIF XML extrait': 'تم استخراج TEIF XML',

  // ——— Retenue TEJ ———
  'Retenue à la source — TEJ': 'الخصم من المورد — TEJ',
  'Exportez votre déclaration de retenue à la source au format XML depuis le portail TEJ (Tunisie TradeNet), puis importez-la ici. Tasrih remplit le tableau officiel « Retenue à la source » (جدول الخصم من المورد).':
    'صدّر تصريح الخصم من المورد بصيغة XML من بوابة TEJ (Tunisie TradeNet) ثم استورده هنا. يعبّئ تصريح الجدول الرسمي «الخصم من المورد».',
  '1. Portail TEJ': '1. بوابة TEJ',
  'Connectez-vous à TEJ, déclarez la retenue à la source, puis téléchargez le fichier XML de la déclaration.':
    'اتصل ببوابة TEJ، صرّح بالخصم من المورد ثم حمّل ملف XML للتصريح.',
  '2. Importer le XML TEJ': '2. استيراد XML الخاص بـ TEJ',
  'Déclaration de retenue (DeclarationsRS) — un ou plusieurs fichiers':
    'تصريح الخصم (DeclarationsRS) — ملف أو أكثر',
  'Importer les certificats de retenue (XML TEJ)': 'استيراد شهادات الخصم (XML TEJ)',
  'Lecture du XML…': 'قراءة XML…',
  'Pas de retenue ce mois-ci ? Continuez directement vers la déclaration mensuelle.':
    'لا يوجد خصم هذا الشهر؟ تابع مباشرة إلى التصريح الشهري.',
  'Importez au moins un fichier XML TEJ': 'استورد ملف XML واحدًا على الأقل',

  // ——— Formulaire / Déclaration ———
  'Déclaration mensuelle': 'التصريح الشهري',
  'Avant d’ouvrir le formulaire': 'قبل فتح الاستمارة',
  'Répondez à la question sur les retenues à la source': 'أجب عن سؤال الخصم من المورد',
  'Répondez à la question sur le personnel': 'أجب عن سؤال الأعوان',
  'Montants pour la déclaration': 'المبالغ الخاصة بالتصريح',
  'Cases cochées': 'الخانات المؤشَّرة',
  'Taxes applicables / sans objet': 'الأداءات المستوجبة / غير المعنية',
  'Aucune': 'لا شيء',
  'À vérifier': 'يجب التحقق',
  '— sans objet': '— غير معني',
  'Rubriques à remplir': 'البنود الواجب تعبئتها',
  'Les valeurs proposées viennent des factures TEIF, des certificats TEJ et des fiches de paie. Corrigez-les si besoin puis appliquez le recalcul.':
    'القيم المقترحة تأتي من فواتير TEIF وشهادات TEJ وبطاقات الأجر. صحّحها عند الحاجة ثم أعد الحساب.',
  '1. Retenue à la source (certificats TEJ)': '1. الخصم من المورد (شهادات TEJ)',
  '2-3. TFP & FOPROLOS (masse salariale brute)': '2-3. التكوين المهني وصندوق النهوض بالمسكن (الأجور الخام)',
  '4. TVA collectée / déductible': '4. الأداء على القيمة المضافة المستوجب / القابل للخصم',
  '6. Droit de timbre fiscal (1 DT / facture encaissée)': '6. معلوم الطابع الجبائي (1 دينار / فاتورة مقبوضة)',
  '7. Taxe hôtelière (2%)': '7. المعلوم على النزل (2%)',
  'Total retenues (TND)': 'مجموع الخصم من المورد (د.ت)',
  'Masse salariale brute (TND)': 'الأجور الخام (د.ت)',
  'TFP — assiette (TND)': 'التكوين المهني — الأساس (د.ت)',
  'TFP — taux en fraction (0.01 manufacture / 0.02 autres)': 'التكوين المهني — النسبة (0.01 صناعي / 0.02 غيره)',
  'TFP — montant (TND)': 'التكوين المهني — المبلغ (د.ت)',
  'FOPROLOS — assiette (TND)': 'صندوق النهوض بالمسكن — الأساس (د.ت)',
  'FOPROLOS — montant (1%)': 'صندوق النهوض بالمسكن — المبلغ (1%)',
  'CA HT 7%': 'رقم المعاملات قبل الأداء 7%',
  'CA HT 13%': 'رقم المعاملات قبل الأداء 13%',
  'CA HT 19%': 'رقم المعاملات قبل الأداء 19%',
  'TVA collectée (TND)': 'الأداء على القيمة المضافة المستوجب (د.ت)',
  'TVA déductible (achats)': 'الأداء على القيمة المضافة القابل للخصم (المشتريات)',
  'CA HT total': 'مجموع رقم المعاملات قبل الأداء',
  'TVA nette due': 'الأداء على القيمة المضافة الصافي المستوجب',
  'Retenue à la source': 'الخصم من المورد',
  'Droit de timbre': 'معلوم الطابع الجبائي',
  'Taxe hôtelière': 'المعلوم على النزل',
  'Taxe sur les établissements': 'المعلوم على المؤسسات',
  'Droit de consommation': 'المعلوم على الاستهلاك',
  'Droit de licence': 'معلوم الإجازة',
  'Autres taxes sur CA': 'معاليم أخرى على رقم المعاملات',

  // ——— Messages / erreurs ———
  'Erreur carte fiscale': 'خطأ في البطاقة الجبائية',
  'Erreur RNE': 'خطأ في مضمون السجل',
  'Erreur onboarding': 'خطأ في الإعداد',
  'Erreur connexion': 'خطأ في الاتصال',
  'Erreur calcul': 'خطأ في الحساب',
  'Erreur calcul de la paie': 'خطأ في حساب الأجور',
  'Erreur upload employé': 'خطأ في رفع وثائق العون',
  'Erreur certificats de retenue TEJ': 'خطأ في شهادات الخصم من المورد',
  'Erreur factures': 'خطأ في الفواتير',
  'Export retenue échoué': 'فشل تصدير الخصم من المورد',
  'Export échoué': 'فشل التصدير',
  'Session expirée': 'انتهت الجلسة',
  'PDF vide': 'ملف PDF فارغ',
  'Lecteur': 'القارئ',

  // ——— Domaine / applicabilité ———
  "Quel est votre domaine d'activité ?": 'ما هو مجال نشاطك؟',
  'Hôtellerie / tourisme': 'الفندقة / السياحة',
  'Agriculture / pêche': 'الفلاحة / الصيد',
  'Industrie / fabrication': 'الصناعة / التصنيع',
  'Commerce / distribution': 'التجارة / التوزيع',
  'Services / conseil / informatique': 'الخدمات / الاستشارة / الإعلامية',
  'Profession libérale': 'مهنة حرة',
  Association: 'جمعية',
  'Droit de consommation (alcool, tabac, ciment…)': 'المعلوم على الاستهلاك (كحول، تبغ، إسمنت…)',
  'Autres taxes sur CA (fonds tourisme, fonds compensation agricole…)':
    'معاليم أخرى على رقم المعاملات (صندوق السياحة، صندوق التعويض الفلاحي…)',
  "Sans objet pour ce domaine d'activité.": 'غير معني بهذا المجال من النشاط.',
  "Applicable selon l'activité / les réponses.": 'مستوجب حسب النشاط / الأجوبة.',

  // ——— Messages de Karim (backend) ———
  'Bonjour, je suis Karim, votre assistant Tasrih. Créez votre compte ou connectez-vous, et je vous guiderai pas à pas pour préparer votre déclaration mensuelle.':
    'مرحبًا، أنا كريم، مساعدك في تصريح. أنشئ حسابك أو سجّل الدخول وسأرافقك خطوة بخطوة لإعداد تصريحك الشهري.',
  'Vous êtes sur votre accueil Tasrih. Commencez ou reprenez votre déclaration, ou scannez vos documents. Dites-moi si vous avez besoin d’aide.':
    'أنت في الصفحة الرئيسية لتصريح. ابدأ أو تابع تصريحك، أو امسح وثائقك. أخبرني إن احتجت مساعدة.',
  'Indiquez si vous avez du personnel. Si oui, vous devrez déposer le contrat de travail, la fiche CNSS et la fiche de paie de chaque employé.':
    'حدّد إن كان لديك أعوان. إذا نعم، ستودع عقد العمل وبطاقة الأجر لكل عون.',
  'Choisissez comment vous déposez habituellement vos déclarations. Cela m’aide à personnaliser votre parcours.':
    'اختر الطريقة المعتادة لإيداع تصريحاتك. يساعدني ذلك على تخصيص مسارك.',
  'Dernière question : un expert-comptable gère-t-il votre paie ou vos déclarations ? Répondez, puis nous passons aux documents.':
    'السؤال الأخير: هل يدير خبير محاسب أجورك أو تصريحاتك؟ أجب ثم ننتقل إلى الوثائق.',
  'Pour commencer, indiquez votre IS de l’année précédente : le montant ou la référence de votre impôt sur les sociétés.':
    'للبدء، أدخل الضريبة على الشركات للسنة الفارطة: المبلغ أو مرجع الضريبة.',
  'Téléversez d’abord votre carte d’identification fiscale, puis l’extrait RNE. Utilisez une image nette : je lis le matricule et l’activité.':
    'حمّل أولاً بطاقة التعريف الجبائي ثم مضمون السجل الوطني. استعمل صورة واضحة: أقرأ المعرّف والنشاط.',
  'Importez vos factures électroniques au format XML TEIF, exportées depuis El Fatoora. Je calcule automatiquement la TVA, le timbre et le chiffre d’affaires.':
    'استورد فواتيرك الإلكترونية بصيغة XML TEIF من فاطورة. أحسب تلقائيًا الأداء على القيمة المضافة والطابع ورقم المعاملات.',
  'Étape retenue à la source : si vous avez payé des montants soumis à retenue, exportez le fichier XML depuis le portail TEJ (tej.finances.gov.tn) puis importez-le ici. Je remplis le tableau officiel « Retenue à la source ». Sinon, continuez directement vers la déclaration mensuelle.':
    'مرحلة الخصم من المورد: إن دفعت مبالغ خاضعة للخصم، صدّر ملف XML من بوابة TEJ ثم استورده هنا. أعبّئ الجدول الرسمي «الخصم من المورد». وإلا، تابع مباشرة إلى التصريح الشهري.',
  'La déclaration est prête. Vérifiez les montants affichés, puis ouvrez le formulaire officiel prérempli. Relisez toujours avant le dépôt.':
    'التصريح جاهز. تحقّق من المبالغ المعروضة ثم افتح الاستمارة الرسمية المعبأة مسبقًا. راجع دائمًا قبل الإيداع.',
  'Vérifiez le profil extrait, surtout le matricule fiscal et la forme juridique. Corrigez directement si une valeur est fausse, puis validez le mois et l’année.':
    'تحقّق من الملف المستخرج، خاصة المعرّف الجبائي والشكل القانوني. صحّح مباشرة إن كانت قيمة خاطئة ثم أكّد الشهر والسنة.',
  // Suggestions
  'Comment créer un compte ?': 'كيف أنشئ حسابًا؟',
  'À quoi sert Tasrih ?': 'ما فائدة تصريح؟',
  'Est-ce gratuit ?': 'هل الخدمة مجانية؟',
  "C'est quoi l'IS ?": 'ما هي الضريبة على الشركات؟',
  'Où trouver mon IS ?': 'أين أجد الضريبة على الشركات؟',
  'Pourquoi ces questions ?': 'لماذا هذه الأسئلة؟',
  'Où trouver la fiche CNSS ?': 'أين أجد بطاقة الضمان الاجتماعي؟',
  'Où trouver la fiche de paie ?': 'أين أجد بطاقة الأجر؟',
  'Formats acceptés ?': 'الصيغ المقبولة؟',
  'Où trouver mon matricule fiscal ?': 'أين أجد معرّفي الجبائي؟',
  "Où trouver l'extrait RNE ?": 'أين أجد مضمون السجل الوطني؟',
  "Mon scan n'est pas lu ?": 'لماذا لا تُقرأ وثيقتي؟',
  'Quelle est ma forme juridique ?': 'ما هو شكلي القانوني؟',
  "Qu'est-ce que le code TVA ?": 'ما هو رمز الأداء على القيمة المضافة؟',
  'Dois-je tout vérifier ?': 'هل يجب التحقق من كل شيء؟',
  'Où exporter mes factures Fatoora ?': 'من أين أصدّر فواتير فاطورة؟',
  'Pourquoi uniquement du XML ?': 'لماذا XML فقط؟',
  "Et si j'ai un achat ?": 'وماذا لو كانت لدي مشتريات؟',
  'Où trouver le XML sur TEJ ?': 'أين أجد XML في TEJ؟',
  "C'est quoi la retenue à la source ?": 'ما هو الخصم من المورد؟',
  'Puis-je passer cette étape ?': 'هل يمكنني تخطي هذه المرحلة؟',
  'Comment vérifier les montants ?': 'كيف أتحقق من المبالغ؟',
  "C'est quoi le timbre ?": 'ما هو الطابع الجبائي؟',
  'Puis-je déposer ce PDF ?': 'هل يمكنني إيداع هذا الملف؟',
  "Désolé, je n'arrive pas à répondre pour le moment. Réessayez dans un instant.":
    'عذرًا، لا أستطيع الإجابة الآن. أعد المحاولة بعد لحظة.',

  // ——— Termes récurrents dans les chaînes dynamiques ———
  'Base ': 'الأساس ',
  'Taux ': 'النسبة ',
  'Montant ': 'المبلغ ',
  'confiance': 'الثقة',
  'Contrat ': 'العقد ',
  'CNSS': 'الضمان الاجتماعي',
  'Paie ': 'الأجر ',
  'Bénéficiaire': 'المستفيد',
  'Certificat': 'شهادة',
  'Nombre d’opérations': 'عدد العمليات',
  'Total retenue': 'مجموع الخصم',
  'déclaration(s) TEJ': 'تصريح (تصاريح) TEJ',
  'fiche(s) de paie': 'بطاقة (بطاقات) أجر',
  'employé': 'عون',
  'facture': 'فاتورة',
  'factures': 'فواتير',
  'Document généré par Tasrih — à vérifier avant dépôt.':
    'وثيقة مُنشأة بواسطة تصريح — يجب التحقق منها قبل الإيداع.',
  'sans objet': 'غير معني',
  'applicable': 'مستوجب',

  // ——— Fragments (texte coupé par <strong>) et libellés restants ———
  'Continuer vers la retenue (TEJ)': 'المتابعة إلى الخصم من المورد',
  'Recalculer avec la réponse': 'إعادة الحساب مع الجواب',
  Rescanner: 'إعادة المسح',
  'Domaine d’activité :': 'مجال النشاط:',
  'Importez le fichier': 'استورد الملف',
  'XML TEIF': 'XML TEIF',
  'TEJ': 'TEJ',
  'carte d’identification fiscale': 'بطاقة التعريف الجبائي',
  'contrat de travail': 'عقد العمل',
  'extrait RNE': 'مضمون السجل الوطني',
  'fiche CNSS': 'بطاقة الضمان الاجتماعي',
  'fiche de paie': 'بطاقة الأجر',
  'Téléversez la': 'حمّل',
  'de la déclaration.': 'للتصريح.',
  'Avez-vous effectué des retenues à la source ?': 'هل قمت بالخصم من المورد؟',
  'exporté depuis El Fatoora / TTN. Tasrih lit HT, TVA, TTC, timbre et lignes, puis remplit la déclaration mensuelle.':
    'مُصدَّر من فاطورة / TTN. يقرأ تصريح الجملة قبل الأداء والأداء على القيمة المضافة والجملة بكل الأداءات والطابع والأسطر ثم يعبّئ التصريح الشهري.',
  'Connectez-vous à TEJ, déclarez la retenue à la source, puis téléchargez le fichier':
    'اتصل ببوابة TEJ، صرّح بالخصم من المورد ثم حمّل ملف',
  'Exportez votre déclaration de retenue à la source au format XML depuis le portail':
    'صدّر تصريح الخصم من المورد بصيغة XML من بوابة',
  'PDF = mensuelle2026 officiel (12 pages) prérempli. Ctrl+S pour enregistrer. Vérifiez avant dépôt.':
    'ملف PDF = الاستمارة الرسمية mensuelle2026 (12 صفحة) معبأة مسبقًا. اضغط Ctrl+S للحفظ. تحقّق قبل الإيداع.',
  'CA brut établissement hôtelier': 'رقم المعاملات الخام للمؤسسة الفندقية',
  'Crédit TVA reporté (mois précédent)': 'رصيد الأداء على القيمة المضافة المرحّل (الشهر الفارط)',
  'Crédit TVA à reporter': 'رصيد الأداء على القيمة المضافة المرحّل',
  'Droit de timbre total (TND)': 'مجموع معلوم الطابع الجبائي (د.ت)',
  'Montant taxe hôtelière (TND)': 'مبلغ المعلوم على النزل (د.ت)',
  'Nombre de factures encaissées': 'عدد الفواتير المقبوضة',
  'TVA nette due (TND)': 'الأداء على القيمة المضافة الصافي المستوجب (د.ت)',
  'et la': 'و',
  'et l’': 'و',
  'Canal de dépôt': 'قناة الإيداع',
  'Pour chaque employé, déposez le': 'لكل عون، أودع',

  // ——— Vérification des documents extraits ———
  'Vérification des documents': 'التحقق من الوثائق',
  'Non extrait': 'لم يُستخرج',
  'Confirmer et continuer': 'تأكيد ومتابعة',
  'Modifier les documents': 'تعديل الوثائق',
  'Corriger le profil': 'تصحيح الملف',
  'Établissement secondaire': 'المؤسسة الثانوية',
  'Activité principale': 'النشاط الرئيسي',
  'Dénomination': 'التسمية',
  'Adresse (siège)': 'العنوان (المقر)',
  'Date d’immatriculation': 'تاريخ التسجيل',
  'Capital': 'رأس المال',
  'Confiance :': 'الثقة:',
  'Voici ce qui a été extrait de la carte fiscale et de l’extrait RNE.':
    'هذا ما تم استخراجه من بطاقة التعريف الجبائي ومضمون السجل الوطني.',
  'Corrigez directement les valeurs fausses': 'صحّح مباشرة القيم الخاطئة',
  'les champs vides sont marqués « Non extrait ») — vos corrections seront utilisées pour la déclaration.':
    'الحقول الفارغة معلّمة «لم يُستخرج» — ستُعتمد تصحيحاتك في التصريح.',
}

/** Phrases remplacées uniquement si le texte entier correspond (connecteurs). */
const EXACT_ONLY = new Set<string>(['et la', 'et l’'])

const PHRASES: Record<string, string> = {
  ...Object.fromEntries(Object.entries(DICT).map(([k, v]) => [k, v.ar])),
  ...EXTRA_PHRASES,
}

/** Clés triées du plus long au plus court (évite les remplacements partiels). */
const PHRASE_KEYS = Object.keys(PHRASES).sort((a, b) => b.length - a.length)

/** Traduit un texte arbitraire vers l'arabe (ou renvoie tel quel si fr/absent). */
export function translateText(input: string, lang: Lang): string {
  if (!input || lang !== 'ar') return input
  const trimmed = input.trim()
  if (!trimmed) return input
  const direct = PHRASES[trimmed]
  if (direct) return input.replace(trimmed, direct)
  let out = input
  for (const key of PHRASE_KEYS) {
    if (EXACT_ONLY.has(key)) continue
    if (out.includes(key)) out = out.split(key).join(PHRASES[key])
  }
  return out
}

// ——— Traducteur DOM (couvre tout le texte, y compris dynamique) ———
const ATTRS = ['placeholder', 'title', 'aria-label', 'alt']
const originals = new WeakMap<Text, string>()
const attrOriginals = new WeakMap<Element, Record<string, string>>()
const touchedText = new Set<Text>()
const touchedEls = new Set<Element>()

function shouldSkip(el: Element | null): boolean {
  if (!el) return true
  const tag = el.tagName
  if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'TEXTAREA' || tag === 'CODE') return true
  return Boolean(el.closest('[data-no-i18n]'))
}

function applyText(t: Text) {
  const cur = t.nodeValue || ''
  if (!/[A-Za-zÀ-ÿ]/.test(cur)) return
  let src = originals.get(t)
  if (src === undefined) src = cur
  const already = translateText(src, 'ar')
  if (cur === already) return
  // Nouvelle valeur fournie par React : elle devient la source.
  originals.set(t, cur)
  const out = translateText(cur, 'ar')
  if (out !== cur) {
    touchedText.add(t)
    t.nodeValue = out
  }
}

function applyAttrs(el: Element) {
  for (const a of ATTRS) {
    const v = el.getAttribute(a)
    if (!v || !/[A-Za-zÀ-ÿ]/.test(v)) continue
    let store = attrOriginals.get(el)
    if (!store) {
      store = {}
      attrOriginals.set(el, store)
    }
    const src = store[a] ?? v
    if (v === translateText(src, 'ar')) continue
    store[a] = v
    const out = translateText(v, 'ar')
    if (out !== v) {
      touchedEls.add(el)
      el.setAttribute(a, out)
    }
  }
}

function translateTree(root: Node) {
  if (root.nodeType === Node.TEXT_NODE) {
    const t = root as Text
    if (!shouldSkip(t.parentElement)) applyText(t)
    return
  }
  if (root.nodeType !== Node.ELEMENT_NODE) return
  const el = root as Element
  if (!shouldSkip(el)) applyAttrs(el)
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (n) => (shouldSkip(n.parentElement) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
  })
  let n: Node | null
  while ((n = walker.nextNode())) applyText(n as Text)
  ;(root as Element).querySelectorAll?.('*').forEach((child) => {
    if (!shouldSkip(child)) applyAttrs(child)
  })
}

function restoreAll() {
  touchedText.forEach((t) => {
    const src = originals.get(t)
    if (src !== undefined && t.isConnected) t.nodeValue = src
  })
  touchedEls.forEach((el) => {
    const store = attrOriginals.get(el)
    if (store && el.isConnected) for (const [a, v] of Object.entries(store)) el.setAttribute(a, v)
  })
  touchedText.clear()
  touchedEls.clear()
}

type I18nValue = {
  lang: Lang
  dir: Dir
  setLang: (lang: Lang) => void
  toggle: () => void
  t: (key: string, vars?: Record<string, string | number>) => string
  tr: (text: string) => string
}

const I18nContext = createContext<I18nValue | null>(null)

const STORAGE_KEY = 'tasrih_lang'

function initialLang(): Lang {
  if (typeof window === 'undefined') return 'fr'
  const urlLang = new URLSearchParams(window.location.search).get('lang')
  if (urlLang === 'fr' || urlLang === 'ar') return urlLang
  const stored = window.localStorage.getItem(STORAGE_KEY)
  if (stored === 'fr' || stored === 'ar') return stored
  return navigator.language?.toLowerCase().startsWith('ar') ? 'ar' : 'fr'
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang)
  const dir: Dir = lang === 'ar' ? 'rtl' : 'ltr'

  useEffect(() => {
    const root = document.documentElement
    root.lang = lang
    root.dir = dir
    window.localStorage.setItem(STORAGE_KEY, lang)
  }, [lang, dir])

  // Traduction globale du DOM en mode arabe (+ observer pour le contenu dynamique).
  useEffect(() => {
    if (lang !== 'ar') {
      restoreAll()
      return
    }
    document.body.setAttribute('dir', 'rtl')
    translateTree(document.body)
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.type === 'characterData') {
          applyText(m.target as Text)
        } else if (m.type === 'childList') {
          m.addedNodes.forEach((n) => translateTree(n))
        } else if (m.type === 'attributes' && m.target instanceof Element) {
          applyAttrs(m.target)
        }
      }
    })
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
      attributes: true,
      attributeFilter: ATTRS,
    })
    return () => observer.disconnect()
  }, [lang])

  const t = useCallback(
    (key: string, vars?: Record<string, string | number>) => {
      const entry = DICT[key]
      let out = entry ? (lang === 'ar' ? entry.ar : entry.fr) : key
      if (vars) {
        for (const [k, v] of Object.entries(vars)) {
          out = out.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
        }
      }
      return out
    },
    [lang],
  )

  const tr = useCallback((text: string) => translateText(text, lang), [lang])

  const value = useMemo<I18nValue>(
    () => ({
      lang,
      dir,
      setLang: setLangState,
      toggle: () => setLangState((l) => (l === 'fr' ? 'ar' : 'fr')),
      t,
      tr,
    }),
    [lang, dir, t, tr],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n must be used within <I18nProvider>')
  return ctx
}

/** Bouton FR ⇄ ع (placez-le dans les barres supérieures). */
export function LangToggle({ className = '' }: { className?: string }) {
  const { lang, setLang } = useI18n()
  return (
    <div className={`lang-toggle ${className}`.trim()} role="group" aria-label="Langue / اللغة">
      <button
        type="button"
        className={lang === 'fr' ? 'on' : ''}
        aria-pressed={lang === 'fr'}
        onClick={() => setLang('fr')}
      >
        FR
      </button>
      <button
        type="button"
        className={lang === 'ar' ? 'on' : ''}
        aria-pressed={lang === 'ar'}
        onClick={() => setLang('ar')}
      >
        ع
      </button>
    </div>
  )
}
