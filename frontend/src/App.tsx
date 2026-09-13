import { FormEvent, useEffect, useMemo, useState } from 'react'
import AssistantWidget from './agent/AssistantWidget'
import type { AgentContext } from './agent/types'
import { LangToggle, useI18n } from './i18n'

const API = import.meta.env.VITE_API_URL || '/api'
const TOKEN_KEY = 'tasrih_token'

type User = { id: number; email: string; phone: string }

type ProfileDraft = {
  name: string
  tax_id: string
  address: string
  activity: string
  vat_code: string
  category_code: string
  secondary_establishment: string
  vat_status: string
  rne_identifier: string
  commercial_name: string
  legal_form: string
}

const EMPTY_PROFILE: ProfileDraft = {
  name: '',
  tax_id: '',
  address: '',
  activity: '',
  vat_code: '',
  category_code: '',
  secondary_establishment: '000',
  vat_status: '',
  rne_identifier: '',
  commercial_name: '',
  legal_form: '',
}

type CIF = {
  tax_id?: string | null
  vat_code?: string | null
  category_code?: string | null
  secondary_establishment?: string | null
  name?: string | null
  main_activity?: string | null
  address?: string | null
  vat_status?: string | null
  subject_to_vat?: boolean | null
  confidence: number
  warnings: string[]
}

type RNE = {
  rne_identifier?: string | null
  company_name?: string | null
  commercial_name?: string | null
  commercial_name_latin?: string | null
  legal_form?: string | null
  capital?: number | null
  registered_address?: string | null
  main_activity?: string | null
  company_status?: string | null
  registration_date?: string | null
  activity_start_date?: string | null
  confidence: number
  warnings: string[]
}

type Invoice = {
  filename: string
  invoice_number?: string | null
  invoice_date?: string | null
  vendor?: string | null
  client?: string | null
  amount_ht?: number | null
  vat_amount?: number | null
  amount_ttc?: number | null
  stamp_duty?: number | null
  vat_rate?: number | null
  category_guess?: string | null
  confidence: number
  warnings: string[]
}

type Retenue = {
  certificate_number?: string | null
  beneficiary?: string | null
  beneficiary_tax_id?: string | null
  nature?: string | null
  base: number
  rate?: number | null
  amount: number
  source: string
  confidence: number
  warnings: string[]
}

type RetenueOperation = {
  id_type_operation?: string | null
  nature?: string | null
  annee_facturation?: string | null
  montant_ht: number
  taux_rs?: number | null
  taux_tva?: number | null
  montant_tva: number
  montant_ttc: number
  montant_rs: number
  montant_net_servi: number
}

type RetenueCertificate = {
  reference?: string | null
  date_paiement?: string | null
  resident?: boolean
  beneficiary_name?: string | null
  beneficiary_id?: string | null
  beneficiary_id_type?: string | null
  beneficiary_category?: string | null
  beneficiary_address?: string | null
  beneficiary_activity?: string | null
  operations: RetenueOperation[]
  total_ht: number
  total_tva: number
  total_ttc: number
  total_rs: number
  total_net_servi: number
}

type RetenueDeclaration = {
  declarant_id?: string | null
  declarant_category?: string | null
  declarant_name?: string | null
  acte_depot?: string | null
  year?: number | null
  month?: number | null
  certificates: RetenueCertificate[]
  total_ht: number
  total_tva: number
  total_ttc: number
  total_rs: number
  total_net_servi: number
  filename?: string
}

type Payslip = {
  filename: string
  employee_name?: string | null
  period?: string | null
  salaire_brut?: number | null
  cotisations?: number | null
  salaire_net?: number | null
  confidence: number
  warnings: string[]
}

type Gap = {
  id: string
  field: string
  type: string
  question_fr: string
  options: { value: unknown; label: string }[]
}

type EmployeeDoc = {
  id: number
  employee_name: string
  has_contract: boolean
  has_cnss: boolean
  has_payslip: boolean
}

type Filled = {
  profile: {
    name: string
    tax_id: string
    address: string
    activity: string
    vat_code: string
    category_code: string
    secondary_establishment: string
    sector: string
    subject_to_vat: boolean
    rne_identifier?: string | null
    commercial_name?: string | null
    legal_form?: string | null
    vat_status?: string | null
  }
  amounts: {
    ca_ht: number
    ca_ht_19: number
    ca_ht_13: number
    ca_ht_7: number
    tva_collectee: number
    tva_collectee_19: number
    retenues_total: number
    retenue_base_total: number
    masse_salariale_brute: number
    tfp_base: number
    tfp_rate: number
    tfp_amount: number
    foprolos_base: number
    foprolos_rate: number
    foprolos_amount: number
    tva_deductible: number
    tva_nette: number
    tva_credit_report: number
    tva_credit_next: number
    stamp_duty_count: number
    stamp_duty_total: number
    etablissement_tax_base: number
    etablissement_tax_amount: number
    hotel_tax_base: number
    hotel_tax_rate: number
    hotel_tax_amount: number
  }
  retenues: Retenue[]
  payslips: Payslip[]
  checkboxes: Record<string, boolean>
  gap_questions: Gap[]
  confidence: number
  needs_user_review: string[]
  checklist: string[]
  domain?: string
  tax_applicability?: Record<string, boolean>
  tax_lines?: {
    key: string
    label_fr: string
    label_ar: string
    amount_field?: string | null
    applicable: boolean
    mark: string
    reason: string
  }[]
  sans_objet?: string[]
}

type Onboarding = {
  previous_is: string
  has_personnel: boolean | null
  declaration_channel: string
  accountant_manages: boolean | null
}

const LEGAL_FORMS = [
  { code: 'SA', label: 'SA — Société anonyme' },
  { code: 'SARL', label: 'SARL — Société à responsabilité limitée' },
  {
    code: 'SUARL',
    label: 'SUARL — Société unipersonnelle à responsabilité limitée',
  },
  { code: 'SNC', label: 'SNC — Société en nom collectif' },
  { code: 'SCS', label: 'SCS — Société en commandite simple' },
  { code: 'SCA', label: 'SCA — Société en commandite par actions' },
]

const DECLARATION_CHANNELS = [
  { value: 'en_ligne', label: 'En ligne (portail fiscal)' },
  { value: 'papier', label: 'Dépôt papier' },
  { value: 'expert', label: 'Via expert comptable' },
  { value: 'autre', label: 'Autre' },
]

/** Champs matériels : toute correction au-delà de la tolérance exige un motif (DGI). */
const MATERIAL_AMOUNT_FIELDS = [
  { key: 'ca_ht', label: 'Chiffre d’affaires' },
  { key: 'tva_collectee', label: 'TVA collectée' },
  { key: 'tva_deductible', label: 'TVA déductible' },
  { key: 'retenues_total', label: 'Retenue à la source' },
] as const
const OVERRIDE_TOLERANCE_PCT = 5

/** After login: questions → (employees) → scan → profil → factures → formulaire */
const STEPS = [
  'Documents',
  'Questions',
  'Personnel',
  'Profil',
  'Factures',
  'Retenue TEJ',
  'Formulaire',
] as const

function authHeaders(token: string | null): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function AmountRow({
  label,
  field,
  amounts,
  edits,
  onEdit,
  step = '0.001',
}: {
  label: string
  field: string
  amounts: Record<string, number>
  edits: Record<string, number>
  onEdit: (field: string, raw: string) => void
  step?: string
}) {
  const value = edits[field] ?? amounts[field] ?? 0
  return (
    <label className="amount-row">
      <span>{label}</span>
      <input
        type="number"
        step={step}
        value={value}
        onChange={(e) => onEdit(field, e.target.value)}
      />
    </label>
  )
}

/** Ligne de vérification éditable d'un champ extrait (ou « Non extrait »). */
function ExtractRow({
  label,
  value,
  onChange,
}: {
  label: string
  value: unknown
  onChange?: (v: string) => void
}) {
  const has = value !== null && value !== undefined && String(value).trim() !== ''
  return (
    <div className={`extract-row${has ? '' : ' missing'}`}>
      <span className="extract-label">{label}</span>
      {onChange ? (
        <input
          className="extract-input"
          value={value === null || value === undefined ? '' : String(value)}
          placeholder="Non extrait"
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <span className="extract-value">{has ? String(value) : 'Non extrait'}</span>
      )}
    </div>
  )
}


export default function App() {
  const { t } = useI18n()
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<User | null>(null)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register')
  const [authForm, setAuthForm] = useState({ email: '', password: '', phone: '' })
  const [showAuth, setShowAuth] = useState(false)
  const [booting, setBooting] = useState(Boolean(token))

  const [step, setStep] = useState(0)
  /** 0=IS · 1=personnel · 2=canal dépôt · 3=expert comptable */
  const [qIndex, setQIndex] = useState(0)
  const [onboarding, setOnboarding] = useState<Onboarding>({
    previous_is: '',
    has_personnel: null,
    declaration_channel: '',
    accountant_manages: null,
  })
  const [employees, setEmployees] = useState<EmployeeDoc[]>([])
  const [empName, setEmpName] = useState('')
  const [empContract, setEmpContract] = useState<File | null>(null)
  const [empCnss, setEmpCnss] = useState<File | null>(null)
  const [empPayslip, setEmpPayslip] = useState<File | null>(null)
  const [busyEmp, setBusyEmp] = useState(false)

  const [cif, setCif] = useState<CIF | null>(null)
  const [rne, setRne] = useState<RNE | null>(null)
  const [busyCif, setBusyCif] = useState(false)
  const [busyRne, setBusyRne] = useState(false)
  const [profileDraft, setProfileDraft] = useState<ProfileDraft>({ ...EMPTY_PROFILE })
  const [showSettings, setShowSettings] = useState(false)
  const [busyProfile, setBusyProfile] = useState(false)
  const [profileSaved, setProfileSaved] = useState(false)
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [retenues, setRetenues] = useState<Retenue[]>([])
  const [retenueDecls, setRetenueDecls] = useState<RetenueDeclaration[]>([])
  const [busyRetenue, setBusyRetenue] = useState(false)
  const [payslips, setPayslips] = useState<Payslip[]>([])
  const [amountEdits, setAmountEdits] = useState<Record<string, number>>({})
  const [fieldComments, setFieldComments] = useState<Record<string, string>>({})
  const [busyPayroll, setBusyPayroll] = useState(false)
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [year, setYear] = useState(new Date().getFullYear())
  const [answers, setAnswers] = useState<Record<string, unknown>>({})
  const [filled, setFilled] = useState<Filled | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [spotlight, setSpotlight] = useState<string | null>(null)

  useEffect(() => {
    if (!spotlight) return
    const el = document.querySelector(`[data-spotlight="${spotlight}"]`)
    if (!el) return
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    el.classList.add('spotlight')
    const timer = window.setTimeout(() => {
      el.classList.remove('spotlight')
      setSpotlight(null)
    }, 2800)
    return () => window.clearTimeout(timer)
  }, [spotlight])

  const loggedIn = Boolean(token && user)

  const hasAmountEdits = Object.keys(amountEdits).length > 0
  const amountsOverride = useMemo(() => {
    if (!filled || !hasAmountEdits) return undefined
    const base: Record<string, number> = { ...filled.amounts }
    for (const [key, value] of Object.entries(amountEdits)) {
      base[key] = value
    }
    return base
  }, [filled, amountEdits, hasAmountEdits])

  /** Corrections de champs matériels au-delà de la tolérance → motif obligatoire. */
  const materialOverrides = useMemo(() => {
    if (!filled) return [] as { field: string; label: string; ocr: number; manual: number; delta: number }[]
    const out: { field: string; label: string; ocr: number; manual: number; delta: number }[] = []
    for (const { key, label } of MATERIAL_AMOUNT_FIELDS) {
      const manual = amountEdits[key]
      if (manual === undefined) continue
      const ocr = Number((filled.amounts as unknown as Record<string, number>)[key] ?? 0)
      if (!ocr) continue
      const delta = ((manual - ocr) / Math.abs(ocr)) * 100
      if (Math.abs(delta) > OVERRIDE_TOLERANCE_PCT) {
        out.push({ field: key, label, ocr, manual, delta })
      }
    }
    return out
  }, [filled, amountEdits])

  const payload = useMemo(
    () => ({
      month: { year, month, declaration_code: '0' },
      cif,
      rne,
      invoices,
      retenues,
      payslips,
      answers: {
        ...answers,
        name: profileDraft.name,
        tax_id: profileDraft.tax_id,
        address: profileDraft.address,
        activity: profileDraft.activity,
        vat_code: profileDraft.vat_code,
        category_code: profileDraft.category_code,
        secondary_establishment: profileDraft.secondary_establishment,
        vat_status: profileDraft.vat_status,
        rne_identifier: profileDraft.rne_identifier,
        commercial_name: profileDraft.commercial_name,
        legal_form: profileDraft.legal_form,
        has_employees: onboarding.has_personnel,
      },
    }),
    [year, month, cif, rne, invoices, retenues, payslips, answers, profileDraft, onboarding.has_personnel],
  )

  const agentStep = loggedIn ? step : 0
  const agentContext = useMemo<AgentContext>(
    () => ({
      step: agentStep,
      q_index: agentStep === 1 ? qIndex : null,
      profile: profileDraft,
      cif: cif as Record<string, unknown> | null,
      rne: rne as Record<string, unknown> | null,
      onboarding: onboarding as unknown as Record<string, unknown>,
      employees: employees as unknown as Record<string, unknown>[],
      invoices: invoices as unknown as Record<string, unknown>[],
      amounts: (filled?.amounts as Record<string, unknown>) ?? null,
      needs_user_review: filled?.needs_user_review ?? null,
      confidence: filled?.confidence ?? null,
      logged_in: loggedIn,
    }),
    [agentStep, qIndex, profileDraft, cif, rne, onboarding, employees, invoices, filled, loggedIn],
  )

  useEffect(() => {
    if (!token) {
      setBooting(false)
      return
    }
    void (async () => {
      try {
        const res = await fetch(`${API}/auth/me`, { headers: authHeaders(token) })
        if (!res.ok) throw new Error('Session expirée')
        const data = await res.json()
        setUser(data.user)
        if (data.profile && typeof data.profile === 'object') {
          setProfileDraft({
            ...EMPTY_PROFILE,
            ...Object.fromEntries(
              Object.keys(EMPTY_PROFILE).map((k) => [
                k,
                String((data.profile as Record<string, unknown>)[k] ?? EMPTY_PROFILE[k as keyof ProfileDraft]),
              ]),
            ),
          })
        }
        if (data.onboarding?.previous_is != null) {
          setOnboarding({
            previous_is: data.onboarding.previous_is || '',
            has_personnel: data.onboarding.has_personnel ?? null,
            declaration_channel: data.onboarding.declaration_channel || '',
            accountant_manages: data.onboarding.accountant_manages ?? null,
          })
        }
        setEmployees(data.employees || [])
        setQIndex(0)
        // Après connexion : directement les documents fiscaux, puis les questions.
        setStep(3)
      } catch {
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
        setUser(null)
      } finally {
        setBooting(false)
      }
    })()
  }, [token])

  async function submitAuth(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const path = authMode === 'register' ? '/auth/register' : '/auth/login'
      const body =
        authMode === 'register'
          ? authForm
          : { email: authForm.email, password: authForm.password }
      const res = await fetch(`${API}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      localStorage.setItem(TOKEN_KEY, data.token)
      setToken(data.token)
      setUser(data.user)
      setShowAuth(false)
      // Après connexion/inscription on démarre par le dépôt des documents fiscaux.
      setStep(3)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur connexion')
    } finally {
      setBusy(false)
    }
  }

  async function logout() {
    if (token) {
      await fetch(`${API}/auth/logout`, {
        method: 'POST',
        headers: authHeaders(token),
      }).catch(() => undefined)
    }
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
    setShowSettings(false)
    setProfileDraft({ ...EMPTY_PROFILE })
    setStep(3)
    setQIndex(0)
    setFilled(null)
    setInvoices([])
    setCif(null)
    setRne(null)
  }

  async function persistOnboarding(data: Onboarding = onboarding) {
    const res = await fetch(`${API}/onboarding`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify(data),
    })
    if (!res.ok) throw new Error(await res.text())
  }

  async function advanceQuestion() {
    setError(null)
    if (qIndex === 0) {
      if (!onboarding.previous_is.trim()) {
        setError('Indiquez votre IS de l’année précédente')
        return
      }
      setQIndex(1)
      return
    }
    if (qIndex === 1) {
      if (onboarding.has_personnel === null) {
        setError('Répondez à la question sur le personnel')
        return
      }
      if (onboarding.has_personnel) {
        setBusy(true)
        try {
          await persistOnboarding()
          setStep(2)
        } catch (err) {
          setError(err instanceof Error ? err.message : 'Erreur onboarding')
        } finally {
          setBusy(false)
        }
        return
      }
      setQIndex(2)
      return
    }
    if (qIndex === 2) {
      if (!onboarding.declaration_channel) {
        setError('Indiquez comment vous déposez vos déclarations')
        return
      }
      setQIndex(3)
      return
    }
    if (qIndex === 3) {
      if (onboarding.accountant_manages === null) {
        setError('Indiquez si un expert comptable gère votre paie / déclarations')
        return
      }
      setBusy(true)
      try {
        await persistOnboarding()
        setStep(4)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erreur onboarding')
      } finally {
        setBusy(false)
      }
    }
  }

  function answerPersonnel(yes: boolean) {
    const next = { ...onboarding, has_personnel: yes }
    setOnboarding(next)
    setError(null)
    if (yes) {
      setBusy(true)
      void persistOnboarding(next)
        .then(() => setStep(2))
        .catch((err) =>
          setError(err instanceof Error ? err.message : 'Erreur onboarding'),
        )
        .finally(() => setBusy(false))
    }
  }

  async function uploadEmployee(e: FormEvent) {
    e.preventDefault()
    if (!empName.trim()) {
      setError('Nom de l’employé requis')
      return
    }
    if (!empContract && !empCnss && !empPayslip) {
      setError('Ajoutez le contrat de travail, la fiche CNSS et/ou la fiche de paie')
      return
    }
    setBusyEmp(true)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('employee_name', empName.trim())
      if (empContract) fd.append('contract', empContract)
      if (empCnss) fd.append('cnss', empCnss)
      if (empPayslip) fd.append('payslip', empPayslip)
      const res = await fetch(`${API}/employees/docs`, {
        method: 'POST',
        headers: authHeaders(token),
        body: fd,
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setEmployees(data.employees || [])
      setEmpName('')
      setEmpContract(null)
      setEmpCnss(null)
      setEmpPayslip(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur upload employé')
    } finally {
      setBusyEmp(false)
    }
  }

  async function uploadExtract(kind: 'cif' | 'rne' | 'invoice', file: File) {
    const fd = new FormData()
    fd.append('file', file)
    const path =
      kind === 'cif' ? '/extract/cif' : kind === 'rne' ? '/extract/rne' : '/extract/invoice'
    const res = await fetch(`${API}${path}`, { method: 'POST', body: fd })
    if (!res.ok) {
      const raw = await res.text()
      let message = raw
      try {
        const parsed = JSON.parse(raw)
        if (typeof parsed?.detail === 'string') message = parsed.detail
        else if (Array.isArray(parsed?.detail)) message = parsed.detail[0]?.msg || raw
      } catch {
        /* réponse non JSON — garder le texte brut */
      }
      throw new Error(message)
    }
    return res.json()
  }

  function buildProfileFromDocs(nextCif: CIF | null, nextRne: RNE | null): ProfileDraft {
    const next: ProfileDraft = {
      name: nextCif?.name || nextRne?.company_name || '',
      tax_id: nextCif?.tax_id || '',
      address: nextCif?.address || nextRne?.registered_address || '',
      activity: nextCif?.main_activity || nextRne?.main_activity || '',
      vat_code: nextCif?.vat_code || '',
      category_code: nextCif?.category_code || '',
      secondary_establishment: nextCif?.secondary_establishment || '000',
      vat_status: nextCif?.vat_status || '',
      rne_identifier: nextRne?.rne_identifier || '',
      commercial_name:
        nextRne?.commercial_name_latin || nextRne?.commercial_name || '',
      legal_form: nextRne?.legal_form || '',
    }
    setProfileDraft(next)
    return next
  }

  async function persistProfile(draft: ProfileDraft = profileDraft) {
    if (!token) return
    setBusyProfile(true)
    setProfileSaved(false)
    setError(null)
    try {
      const res = await fetch(`${API}/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify(draft),
      })
      if (!res.ok) throw new Error(await res.text())
      setProfileSaved(true)
      window.setTimeout(() => setProfileSaved(false), 2500)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Enregistrement profil échoué')
    } finally {
      setBusyProfile(false)
    }
  }

  async function onCif(files: FileList | null, input: HTMLInputElement) {
    if (!files?.[0]) return
    setBusyCif(true)
    setError(null)
    try {
      const data = await uploadExtract('cif', files[0])
      setCif(data)
      const next = buildProfileFromDocs(data, rne)
      if (rne) {
        void persistProfile(next)
        setStep(8)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur carte fiscale')
    } finally {
      setBusyCif(false)
      input.value = ''
    }
  }

  async function onRne(files: FileList | null, input: HTMLInputElement) {
    if (!files?.[0]) return
    setBusyRne(true)
    setError(null)
    try {
      const data = await uploadExtract('rne', files[0])
      setRne(data)
      const next = buildProfileFromDocs(cif, data)
      if (cif) {
        void persistProfile(next)
        setStep(8)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur RNE')
    } finally {
      setBusyRne(false)
      input.value = ''
    }
  }

  /** Édition manuelle des champs extraits (écran de vérification). */
  function updateCif(patch: Partial<CIF>) {
    setCif((c) => (c ? { ...c, ...patch } : c))
  }

  function updateRne(patch: Partial<RNE>) {
    setRne((r) => (r ? { ...r, ...patch } : r))
  }

  async function onInvoices(files: FileList | null) {
    if (!files?.length) return
    setBusy(true)
    setError(null)
    try {
      const extracted: Invoice[] = []
      for (const file of Array.from(files)) {
        const name = file.name.toLowerCase()
        if (!name.endsWith('.xml') && !name.endsWith('.xlms')) {
          throw new Error(
            `Fichier non TEIF: ${file.name}. Importez le XML Fatoora (ex. TEIF_FAC-….xml).`,
          )
        }
        extracted.push(await uploadExtract('invoice', file))
      }
      setInvoices((prev) => [...prev, ...extracted])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur factures')
    } finally {
      setBusy(false)
    }
  }

  async function onRetenues(files: FileList | null) {
    if (!files?.length) return
    setBusyRetenue(true)
    setError(null)
    try {
      const extracted: Retenue[] = []
      const decls: RetenueDeclaration[] = []
      for (const file of Array.from(files)) {
        const fd = new FormData()
        fd.append('file', file)
        const res = await fetch(`${API}/extract/retenue`, { method: 'POST', body: fd })
        if (!res.ok) throw new Error(await res.text())
        const data = await res.json()
        extracted.push(...(data.retenues || []))
        if (data.declaration) decls.push(data.declaration)
      }
      setRetenues((prev) => [...prev, ...extracted])
      if (decls.length) setRetenueDecls((prev) => [...prev, ...decls])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur certificats de retenue TEJ')
    } finally {
      setBusyRetenue(false)
    }
  }

  function mergeRetenueDecls(decls: RetenueDeclaration[]): RetenueDeclaration | null {
    if (!decls.length) return null
    const base = decls[0]
    const merged: RetenueDeclaration = {
      ...base,
      certificates: decls.flatMap((d) => d.certificates),
      total_ht: 0,
      total_tva: 0,
      total_ttc: 0,
      total_rs: 0,
      total_net_servi: 0,
    }
    for (const d of decls) {
      merged.total_ht += d.total_ht
      merged.total_tva += d.total_tva
      merged.total_ttc += d.total_ttc
      merged.total_rs += d.total_rs
      merged.total_net_servi += d.total_net_servi
    }
    return merged
  }

  async function exportRetenuePdf() {
    const declaration = mergeRetenueDecls(retenueDecls)
    if (!declaration) {
      setError('Importez au moins un fichier XML TEJ')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const res = await fetch(`${API}/export/retenue`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({
          declaration,
          profile: {
            name: profileDraft.name,
            tax_id: profileDraft.tax_id,
            address: profileDraft.address,
            vat_code: profileDraft.vat_code,
            category_code: profileDraft.category_code,
            secondary_establishment: profileDraft.secondary_establishment,
          },
          month: { year, month, declaration_code: '0' },
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const buf = await res.arrayBuffer()
      if (!buf.byteLength) throw new Error('PDF vide')
      const url = URL.createObjectURL(new Blob([buf], { type: 'application/pdf' }))
      window.open(url, '_blank', 'noopener,noreferrer')
      window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export retenue échoué')
    } finally {
      setBusy(false)
    }
  }

  async function loadPayroll() {
    setBusyPayroll(true)
    setError(null)
    try {
      const res = await fetch(`${API}/employees/payroll`, { headers: authHeaders(token) })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      setPayslips(data.payslips || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur calcul de la paie')
    } finally {
      setBusyPayroll(false)
    }
  }

  function editAmount(field: string, raw: string) {
    const value = Number(raw)
    setAmountEdits((prev) => ({ ...prev, [field]: Number.isFinite(value) ? value : 0 }))
  }

  async function runPipeline(extraAnswers?: Record<string, unknown>) {
    setBusy(true)
    setError(null)
    try {
      const answersMerged = extraAnswers
        ? { ...payload.answers, ...extraAnswers }
        : payload.answers
      const res = await fetch(`${API}/pipeline/build`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({
          ...payload,
          answers: answersMerged,
          amounts_override: amountsOverride,
        }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data: Filled = await res.json()
      setFilled(data)
      setStep(6)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur calcul')
    } finally {
      setBusy(false)
    }
  }

  function answerGap(field: string, value: unknown) {
    setAnswers((prev) => ({ ...prev, [field]: value }))
    void runPipeline({ [field]: value })
  }

  /** Enregistre la déclaration + les corrections (avec motifs) côté DGI. */
  async function persistDeclaration() {
    if (!filled || !token) return
    try {
      const a = filled.amounts
      const res = await fetch(`${API}/declarations/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({
          matricule_fiscal: filled.profile.tax_id,
          name: filled.profile.name,
          activite: filled.profile.activity,
          code_tva: filled.profile.vat_code,
          code_categorie: filled.profile.category_code,
          regime: 'reel',
          month,
          year,
          chiffre_affaires_declare: a.ca_ht,
          tva_collectee: a.tva_collectee,
          tva_deductible: a.tva_deductible,
          retenue_totale: a.retenues_total,
          status: 'submitted',
          invoice_count: invoices.length,
          invoice_amount_ht: invoices.reduce((s, i) => s + (i.amount_ht || 0), 0),
          invoice_amount_ttc: invoices.reduce((s, i) => s + (i.amount_ttc || 0), 0),
          invoice_ids: invoices.map((i) => i.invoice_number || i.filename).filter(Boolean),
        }),
      })
      if (!res.ok) return
      const saved = await res.json()
      for (const o of materialOverrides) {
        await fetch(`${API}/declarations/${saved.declaration_id}/field-edit`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
          body: JSON.stringify({
            field_name: o.field,
            ocr_extracted_value: o.ocr,
            manual_value: o.manual,
            comment: fieldComments[o.field] || '',
          }),
        })
      }
    } catch {
      /* l'enregistrement DGI ne bloque pas l'export */
    }
  }

  async function openOfficialPdf(e: FormEvent) {
    e.preventDefault()
    if (answers.does_withholding === undefined) {
      setError('Répondez à la question sur les retenues à la source')
      return
    }
    // Motif obligatoire pour toute correction matérielle au-delà de la tolérance.
    const missingComments = materialOverrides.filter((o) => !(fieldComments[o.field] || '').trim())
    if (missingComments.length) {
      setError(
        `Motif obligatoire pour : ${missingComments.map((m) => m.label).join(', ')} ` +
          `(écart > ${OVERRIDE_TOLERANCE_PCT} % vs valeur extraite).`,
      )
      return
    }
    setBusy(true)
    setError(null)
    try {
      const res = await fetch(`${API}/pipeline/export-official`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ ...payload, amounts_override: amountsOverride }),
      })
      if (!res.ok) throw new Error(await res.text())
      const buf = await res.arrayBuffer()
      if (!buf.byteLength) throw new Error('PDF vide')
      const filename =
        res.headers.get('Content-Disposition')?.match(/filename="?([^"]+)"?/)?.[1] ||
        `declaration_mensuelle_${year}_${String(month).padStart(2, '0')}.pdf`
      const blob = new Blob([buf], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.rel = 'noopener'
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.open(url, '_blank', 'noopener,noreferrer')
      window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
      void persistDeclaration()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export échoué')
    } finally {
      setBusy(false)
    }
  }

  const progressIndex =
    step === 3 || step === 8
      ? 0
      : step === 1
        ? 1
        : step === 2
          ? 2
          : step === 4
            ? 3
            : step === 5
              ? 4
              : step === 7
                ? 5
                : step === 6
                  ? 6
                  : -1

  if (booting) {
    return (
      <div className="app">
        <div className="bg" aria-hidden="true" />
        <div className="shell">
          <p className="lead">Chargement…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      <div className="bg" aria-hidden="true" />
      <div className={loggedIn ? 'shell' : 'shell shell-landing'}>
        {/* —— PUBLIC LANDING + AUTH —— */}
        {!loggedIn && (
          <div className="landing">
            <header className="ft-topbar">
              <div className="ft-topbar-inner">
                <div className="ft-brand">
                  <img
                    src="/tasrih-logo.png"
                    alt="Tasrih"
                    className="ft-logo"
                  />
                </div>
                <div className="ft-actions">
                  <LangToggle />
                  <button
                    type="button"
                    className="ft-btn ft-btn-solid"
                    onClick={() => {
                      setAuthMode('register')
                      setError(null)
                      setShowAuth(true)
                    }}
                  >
                    {t("S'inscrire")}
                  </button>
                  <button
                    type="button"
                    className="ft-btn ft-btn-outline"
                    onClick={() => {
                      setAuthMode('login')
                      setError(null)
                      setShowAuth(true)
                    }}
                  >
                    {t('Se connecter')}
                  </button>
                </div>
              </div>
            </header>

            <main className="ft-main">
              <section className="ef-home-hero">
                <img
                  className="ef-home-hero-logo"
                  src="/tasrih-logo.png"
                  alt="تصريح — Tasrih"
                />
                <h1 className="ef-home-hero-title visually-hidden">Tasrih</h1>
                <p className="ef-home-hero-subtitle">
                  {t(
                    'Plateforme d’aide à la déclaration mensuelle tunisienne : documents fiscaux, factures électroniques Fatoora et formulaire officiel prérempli.',
                  )}
                </p>
              </section>

              <section className="ef-home-steps-section">
                <h2 className="ef-home-steps-title">{t('Votre déclaration en 5 étapes')}</h2>
                <p className="ef-home-steps-subtitle">{t('Un parcours simple et guidé')}</p>
                <div className="ef-home-steps-grid">
                  <div className="ef-home-step-card">
                    <div className="ef-home-step-number">1</div>
                    <div className="ef-home-step-icon" aria-hidden="true">
                      🧾
                    </div>
                    <h3 className="ef-home-step-card-title">{t('Documents fiscaux')}</h3>
                    <p className="ef-home-step-card-desc">
                      {t('Carte d’identification fiscale et extrait RNE lus automatiquement (OCR).')}
                    </p>
                  </div>
                  <div className="ef-home-step-card">
                    <div className="ef-home-step-number">2</div>
                    <div className="ef-home-step-icon" aria-hidden="true">
                      📝
                    </div>
                    <h3 className="ef-home-step-card-title">{t('Questions')}</h3>
                    <p className="ef-home-step-card-desc">
                      {t(
                        'IS, personnel et canal de dépôt : quelques questions pour cadrer votre déclaration.',
                      )}
                    </p>
                  </div>
                  <div className="ef-home-step-card">
                    <div className="ef-home-step-number">3</div>
                    <div className="ef-home-step-icon" aria-hidden="true">
                      📄
                    </div>
                    <h3 className="ef-home-step-card-title">{t('Factures Fatoora')}</h3>
                    <p className="ef-home-step-card-desc">
                      {t('Importez vos factures électroniques TEIF (XML) et calculez la TVA.')}
                    </p>
                  </div>
                  <div className="ef-home-step-card">
                    <div className="ef-home-step-number">4</div>
                    <div className="ef-home-step-icon" aria-hidden="true">
                      🏛️
                    </div>
                    <h3 className="ef-home-step-card-title">{t('Retenue à la source (TEJ)')}</h3>
                    <p className="ef-home-step-card-desc">
                      {t('Exportez le XML sur <strong>tej.finances.gov.tn</strong> puis générez le tableau officiel « Retenue à la source ».')}
                    </p>
                  </div>
                  <div className="ef-home-step-card">
                    <div className="ef-home-step-number">5</div>
                    <div className="ef-home-step-icon" aria-hidden="true">
                      ✅
                    </div>
                    <h3 className="ef-home-step-card-title">{t('Formulaire officiel')}</h3>
                    <p className="ef-home-step-card-desc">
                      {t('Générez la déclaration mensuelle préremplie et exportez le PDF officiel.')}
                    </p>
                  </div>
                </div>
              </section>

              <section className="ef-home-faq-section">
                <h2 className="ef-home-faq-title">{t('Questions Fréquemment Posées')}</h2>
                <p className="ef-home-faq-subtitle">
                  {t('Trouvez rapidement les réponses à vos questions')}
                </p>
                <div className="ef-home-faq-wrap">
                  <details className="ef-faq-item">
                    <summary className="ef-faq-summary">
                      <span>{t('Quels documents faut-il fournir ?')}</span>
                      <span className="ef-faq-caret" aria-hidden="true" />
                    </summary>
                    <div className="ef-faq-body">
                      <p>
                        {t(
                          'La carte d’identification fiscale et l’extrait RNE de votre entreprise, puis vos factures électroniques du mois. Aucun justificatif papier n’est requis.',
                        )}
                      </p>
                    </div>
                  </details>
                  <details className="ef-faq-item">
                    <summary className="ef-faq-summary">
                      <span>{t('Comment mes documents sont-ils lus ?')}</span>
                      <span className="ef-faq-caret" aria-hidden="true" />
                    </summary>
                    <div className="ef-faq-body">
                      <p>
                        {t(
                          'Les informations (matricule fiscal, code TVA, code catégorie, forme juridique…) sont extraites automatiquement par OCR puis vérifiées. Vous pouvez corriger chaque champ avant de continuer.',
                        )}
                      </p>
                    </div>
                  </details>
                  <details className="ef-faq-item">
                    <summary className="ef-faq-summary">
                      <span>{t('Quelles factures puis-je importer ?')}</span>
                      <span className="ef-faq-caret" aria-hidden="true" />
                    </summary>
                    <div className="ef-faq-body">
                      <p>
                        {t(
                          'Les factures électroniques au format TEIF / Fatoora (fichiers XML) émises et reçues. La TVA collectée et déductible est calculée automatiquement.',
                        )}
                      </p>
                    </div>
                  </details>
                  <details className="ef-faq-item">
                    <summary className="ef-faq-summary">
                      <span>{t('Le PDF généré est-il le formulaire officiel ?')}</span>
                      <span className="ef-faq-caret" aria-hidden="true" />
                    </summary>
                    <div className="ef-faq-body">
                      <p>
                        {t(
                          'Oui, la déclaration reprend le formulaire officiel mensuelle2026 (12 pages), prérempli et modifiable. Vérifiez toujours les montants avant le dépôt.',
                        )}
                      </p>
                    </div>
                  </details>
                </div>
              </section>

            </main>

            <footer className="ft-footer">
              <div className="ft-footer-copy">
                {t('Tasrih — Déclaration mensuelle Tunisie © 2026')}
              </div>
              <div className="ft-footer-links">
                <span className="ft-footer-link">{t('Informations légales')}</span>
                <span className="ft-footer-link">{t('Protection des données')}</span>
                <span className="ft-footer-link">{t('Conditions Générales')}</span>
              </div>
            </footer>
          </div>
        )}

        {loggedIn && (
          <>
            <header className="topbar">
              <div className="logo-row">
                <img src="/tasrih-mark.png" alt="" className="logo-mark" width={32} height={32} />
                <p className="logo-mini">Tasrih</p>
              </div>
              <div className="progress">
                {STEPS.map((label, i) => (
                  <i
                    key={label}
                    className={progressIndex === i ? 'on' : progressIndex > i ? 'done' : ''}
                    title={t(label)}
                  />
                ))}
              </div>
              <div className="topbar-actions">
                <LangToggle />
                <div className="topbar-user-block">
                  <button
                    type="button"
                    className="topbar-settings-btn"
                    onClick={() => {
                      setProfileSaved(false)
                      setShowSettings(true)
                    }}
                  >
                    {t('Mes paramètres')}
                  </button>
                  <div className="topbar-user" title={user?.email}>
                    <span className="topbar-avatar" aria-hidden="true">
                      {(user?.email?.[0] || '?').toUpperCase()}
                    </span>
                    <span className="topbar-email">{user?.email}</span>
                  </div>
                </div>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  onClick={() => void logout()}
                >
                  {t('Déconnexion')}
                </button>
              </div>
            </header>

            {showSettings && (
              <div className="settings-modal" role="dialog" aria-modal="true" aria-labelledby="settings-title">
                <div
                  className="settings-modal-backdrop"
                  onClick={() => setShowSettings(false)}
                  aria-hidden="true"
                />
                <div className="settings-modal-card">
                  <header className="settings-head">
                    <div>
                      <p className="settings-kicker">{t('Compte')}</p>
                      <h2 id="settings-title">{t('Paramètres du profil')}</h2>
                      <p className="settings-sub">
                        {t(
                          'Prérempli depuis votre carte fiscale et votre extrait RNE. Modifiez à tout moment, puis enregistrez.',
                        )}
                      </p>
                    </div>
                    <button
                      type="button"
                      className="settings-close"
                      aria-label={t('Fermer')}
                      onClick={() => setShowSettings(false)}
                    >
                      ×
                    </button>
                  </header>

                  <div className="settings-account">
                    <span className="topbar-avatar lg" aria-hidden="true">
                      {(user?.email?.[0] || '?').toUpperCase()}
                    </span>
                    <div>
                      <strong>{user?.email}</strong>
                      {user?.phone ? <span>{user.phone}</span> : null}
                    </div>
                  </div>

                  <div className="profile-card settings-fields">
                    <div className="grid-2">
                      <div className="field">
                        <label>{t('Raison sociale / Nom')}</label>
                        <input
                          value={profileDraft.name}
                          onChange={(e) =>
                            setProfileDraft({ ...profileDraft, name: e.target.value })
                          }
                        />
                      </div>
                      <div className="field">
                        <label>{t('Matricule fiscal')}</label>
                        <input
                          value={profileDraft.tax_id}
                          onChange={(e) =>
                            setProfileDraft({ ...profileDraft, tax_id: e.target.value })
                          }
                        />
                      </div>
                      <div className="field">
                        <label>{t('Code TVA')}</label>
                        <input
                          value={profileDraft.vat_code}
                          onChange={(e) =>
                            setProfileDraft({ ...profileDraft, vat_code: e.target.value })
                          }
                        />
                      </div>
                      <div className="field">
                        <label>{t('Code catégorie')}</label>
                        <input
                          value={profileDraft.category_code}
                          onChange={(e) =>
                            setProfileDraft({ ...profileDraft, category_code: e.target.value })
                          }
                        />
                      </div>
                      <div className="field">
                        <label>{t('Identifiant RNE')}</label>
                        <input
                          value={profileDraft.rne_identifier}
                          onChange={(e) =>
                            setProfileDraft({ ...profileDraft, rne_identifier: e.target.value })
                          }
                        />
                      </div>
                      <div className="field">
                        <label>{t('Nom commercial')}</label>
                        <input
                          value={profileDraft.commercial_name}
                          onChange={(e) =>
                            setProfileDraft({ ...profileDraft, commercial_name: e.target.value })
                          }
                        />
                      </div>
                    </div>
                    <div className="field">
                      <label>{t('Adresse')}</label>
                      <input
                        value={profileDraft.address}
                        onChange={(e) =>
                          setProfileDraft({ ...profileDraft, address: e.target.value })
                        }
                      />
                    </div>
                    <div className="field">
                      <label>{t('Activité')}</label>
                      <input
                        value={profileDraft.activity}
                        onChange={(e) =>
                          setProfileDraft({ ...profileDraft, activity: e.target.value })
                        }
                      />
                    </div>
                    <div className="grid-2">
                      <div className="field">
                        <label>{t('Forme juridique')}</label>
                        <select
                          value={(() => {
                            const cur = profileDraft.legal_form.trim()
                            const byLabel = LEGAL_FORMS.find((f) => f.label === cur)
                            if (byLabel) return byLabel.label
                            const byCode = LEGAL_FORMS.find((f) =>
                              cur.toUpperCase().startsWith(f.code),
                            )
                            return byCode?.label || ''
                          })()}
                          onChange={(e) =>
                            setProfileDraft({ ...profileDraft, legal_form: e.target.value })
                          }
                        >
                          <option value="">{t('Choisir (extrait RNE)…')}</option>
                          {LEGAL_FORMS.map((f) => (
                            <option key={f.code} value={f.label}>
                              {f.label}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div className="field">
                        <label>{t('Statut TVA (carte)')}</label>
                        <input
                          value={profileDraft.vat_status}
                          onChange={(e) =>
                            setProfileDraft({ ...profileDraft, vat_status: e.target.value })
                          }
                        />
                      </div>
                    </div>
                  </div>

                  <div className="settings-actions">
                    {profileSaved && (
                      <p className="settings-saved" role="status">
                        {t('Modifications enregistrées')}
                      </p>
                    )}
                    <button
                      type="button"
                      className="btn btn-ghost"
                      disabled={busyProfile}
                      onClick={() => setShowSettings(false)}
                    >
                      {t('Fermer')}
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={busyProfile}
                      onClick={() => void persistProfile()}
                    >
                      {busyProfile
                        ? t('Enregistrement…')
                        : t('Sauvegarder les modifications')}
                    </button>
                  </div>
                </div>
              </div>
            )}

            {error && <p className="error">{error}</p>}

            {/* —— 1. QUESTIONS (one screen each) —— */}
            {step === 1 && qIndex === 0 && (
              <section className="panel question-screen" data-spotlight="question">
                <p className="q-progress">Question 1 / 4</p>
                <h2>Quel est votre IS de l’année précédente ?</h2>
                <p className="sub">Indiquez le montant ou la référence de votre impôt sur les sociétés.</p>
                <div className="field">
                  <label>IS année précédente</label>
                  <input
                    autoFocus
                    value={onboarding.previous_is}
                    onChange={(e) =>
                      setOnboarding({ ...onboarding, previous_is: e.target.value })
                    }
                    placeholder="Montant ou référence IS"
                  />
                </div>
                <div className="actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busy || !onboarding.previous_is.trim()}
                    onClick={() => void advanceQuestion()}
                  >
                    Continuer
                  </button>
                </div>
              </section>
            )}

            {step === 1 && qIndex === 1 && (
              <section className="panel question-screen" data-spotlight="question">
                <p className="q-progress">Question 2 / 4</p>
                <h2>Avez-vous du personnel ?</h2>
                <p className="sub">
                  Si oui, vous déposerez le contrat de travail et la fiche CNSS pour chaque employé.
                </p>
                <div className="gap-opts">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busy}
                    onClick={() => answerPersonnel(true)}
                  >
                    Oui
                  </button>
                  <button
                    type="button"
                    className={
                      onboarding.has_personnel === false ? 'btn btn-primary' : 'btn btn-ghost'
                    }
                    disabled={busy}
                    onClick={() => {
                      setOnboarding({ ...onboarding, has_personnel: false })
                      setError(null)
                    }}
                  >
                    Non
                  </button>
                </div>
                <div className="actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busy || onboarding.has_personnel !== false}
                    onClick={() => void advanceQuestion()}
                  >
                    Continuer
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => setQIndex(0)}
                  >
                    Retour
                  </button>
                </div>
              </section>
            )}

            {step === 1 && qIndex === 2 && (
              <section className="panel question-screen" data-spotlight="question">
                <p className="q-progress">Question 3 / 4</p>
                <h2>Comment déposez-vous vos déclarations ?</h2>
                <p className="sub">Choisissez votre canal habituel de dépôt.</p>
                <div className="field">
                  <label>Canal de dépôt</label>
                  <select
                    value={onboarding.declaration_channel}
                    onChange={(e) =>
                      setOnboarding({ ...onboarding, declaration_channel: e.target.value })
                    }
                  >
                    <option value="">Choisir…</option>
                    {DECLARATION_CHANNELS.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busy || !onboarding.declaration_channel}
                    onClick={() => void advanceQuestion()}
                  >
                    Continuer
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => setQIndex(1)}
                  >
                    Retour
                  </button>
                </div>
              </section>
            )}

            {step === 1 && qIndex === 3 && (
              <section className="panel question-screen" data-spotlight="question">
                <p className="q-progress">Question 4 / 4</p>
                <h2>Un expert comptable gère-t-il votre paie / déclarations ?</h2>
                <p className="sub">Cela aide à personnaliser les prochaines étapes.</p>
                <div className="gap-opts">
                  <button
                    type="button"
                    className={
                      onboarding.accountant_manages === true
                        ? 'btn btn-primary'
                        : 'btn btn-ghost'
                    }
                    onClick={() =>
                      setOnboarding({ ...onboarding, accountant_manages: true })
                    }
                  >
                    Oui
                  </button>
                  <button
                    type="button"
                    className={
                      onboarding.accountant_manages === false
                        ? 'btn btn-primary'
                        : 'btn btn-ghost'
                    }
                    onClick={() =>
                      setOnboarding({ ...onboarding, accountant_manages: false })
                    }
                  >
                    Non
                  </button>
                </div>
                <div className="actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busy || onboarding.accountant_manages === null}
                    onClick={() => void advanceQuestion()}
                  >
                    Continuer
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => setQIndex(2)}
                  >
                    Retour
                  </button>
                </div>
              </section>
            )}

            {/* —— 2. EMPLOYEES —— */}
            {step === 2 && (
              <section className="panel" data-spotlight="employees">
                <h2>Documents du personnel</h2>
                <p className="sub">
                  Pour chaque employé, déposez le <strong>contrat de travail</strong>, la{' '}
                  <strong>fiche CNSS</strong> et la <strong>fiche de paie</strong>.
                </p>
                <form className="profile-card" onSubmit={(e) => void uploadEmployee(e)}>
                  <div className="field">
                    <label>Nom de l’employé</label>
                    <input value={empName} onChange={(e) => setEmpName(e.target.value)} />
                  </div>
                  <div className="grid-3">
                    <label className={`scan-zone compact${busyEmp ? ' busy' : ''}`}>
                      <input
                        type="file"
                        accept=".pdf,image/*"
                        disabled={busyEmp}
                        onChange={(e) => setEmpContract(e.target.files?.[0] || null)}
                      />
                      <strong>
                        {empContract ? empContract.name : 'Contrat de travail'}
                      </strong>
                      <p>PDF ou photo</p>
                    </label>
                    <div className="scan-zone compact static" aria-disabled="true">
                      <strong>Fiche CNSS</strong>
                      <p>Zone statique — aucun dépôt</p>
                    </div>
                    <label className={`scan-zone compact${busyEmp ? ' busy' : ''}`}>
                      <input
                        type="file"
                        accept=".pdf,image/*"
                        disabled={busyEmp}
                        onChange={(e) => setEmpPayslip(e.target.files?.[0] || null)}
                      />
                      <strong>{empPayslip ? empPayslip.name : 'Fiche de paie'}</strong>
                      <p>PDF ou photo</p>
                    </label>
                  </div>
                  <button type="submit" className="btn btn-ghost" disabled={busyEmp}>
                    {busyEmp ? 'Envoi…' : 'Ajouter cet employé'}
                  </button>
                </form>
                {employees.length > 0 && (
                  <ul className="inv-list">
                    {employees.map((emp) => (
                      <li key={emp.id}>
                        <strong>{emp.employee_name}</strong>
                        <span>
                          Contrat {emp.has_contract ? 'OK' : '—'} · CNSS{' '}
                          {emp.has_cnss ? 'OK' : '—'} · Paie {emp.has_payslip ? 'OK' : '—'}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
                <div className="actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={employees.length === 0}
                    onClick={() => {
                      setQIndex(2)
                      setStep(1)
                    }}
                  >
                    Continuer
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => {
                      setQIndex(1)
                      setStep(1)
                    }}
                  >
                    Retour
                  </button>
                </div>
              </section>
            )}

            {/* —— 3. SCAN CIF + RNE —— */}
            {step === 3 && (
              <section className="panel" data-spotlight="scan">
                <h2>Documents fiscaux</h2>
                <p className="sub">
                  Téléversez la <strong>carte d’identification fiscale</strong> et l’
                  <strong>extrait RNE</strong> — un fichier à la fois.
                </p>
                <div className="grid-2">
                  <label className={`scan-zone${busyCif ? ' busy' : ''}`}>
                    <input
                      type="file"
                      accept=".pdf,image/*"
                      disabled={busyCif || busyRne}
                      onChange={(e) => void onCif(e.target.files, e.target)}
                    />
                    <div className="pulse">CIF</div>
                    <strong>
                      {busyCif
                        ? 'Extraction…'
                        : cif
                          ? 'Carte fiscale chargée'
                          : 'Carte d’identification fiscale'}
                    </strong>
                    <p>
                      {cif
                        ? `${cif.name || 'nom ?'} · ${cif.tax_id || 'matricule ?'} · ${(cif.confidence * 100).toFixed(0)}%`
                        : 'PDF ou photo'}
                    </p>
                    {cif?.warnings?.length ? (
                      <p className="scan-warn">{cif.warnings.slice(0, 2).join(' · ')}</p>
                    ) : null}
                  </label>
                  <label className={`scan-zone${busyRne ? ' busy' : ''}`}>
                    <input
                      type="file"
                      accept=".pdf,image/*"
                      disabled={busyCif || busyRne}
                      onChange={(e) => void onRne(e.target.files, e.target)}
                    />
                    <div className="pulse">RNE</div>
                    <strong>
                      {busyRne
                        ? 'Extraction…'
                        : rne
                          ? 'Extrait RNE chargé'
                          : 'Extrait RNE'}
                    </strong>
                    <p>
                      {rne
                        ? `${rne.commercial_name_latin || rne.company_name || 'raison ?'} · ${rne.rne_identifier || 'id ?'} · ${(rne.confidence * 100).toFixed(0)}%`
                        : 'PDF ou photo'}
                    </p>
                    {rne?.warnings?.length ? (
                      <p className="scan-warn">{rne.warnings.slice(0, 2).join(' · ')}</p>
                    ) : null}
                  </label>
                </div>
                <div className="actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={!cif && !rne}
                    onClick={() => {
                      buildProfileFromDocs(cif, rne)
                      const hasData = Boolean(
                        cif?.tax_id || cif?.name || rne?.rne_identifier || rne?.company_name,
                      )
                      if (!hasData) {
                        setError(
                          'Extraction vide — rescanner une image plus nette (OCR eng activé).',
                        )
                        return
                      }
                      setStep(8)
                    }}
                  >
                    Continuer
                  </button>
                </div>
              </section>
            )}

            {/* —— 8. VÉRIFICATION DES DOCUMENTS EXTRAITS —— */}
            {step === 8 && (
              <section className="panel" data-spotlight="verify">
                <h2>Vérification des documents</h2>
                <p className="sub">
                  Voici ce qui a été extrait de la carte fiscale et de l’extrait RNE.{' '}
                  <strong>Corrigez directement les valeurs fausses</strong> (les champs vides
                  sont marqués « Non extrait ») — vos corrections seront utilisées pour la
                  déclaration.
                </p>

                <div className="result-grid">
                  <div className="block">
                    <h3>Carte d’identification fiscale</h3>
                    <div className="extract-list">
                      <ExtractRow
                        label="Matricule fiscal"
                        value={cif?.tax_id}
                        onChange={(v) => updateCif({ tax_id: v })}
                      />
                      <ExtractRow
                        label="Code TVA"
                        value={cif?.vat_code}
                        onChange={(v) => updateCif({ vat_code: v })}
                      />
                      <ExtractRow
                        label="Code catégorie"
                        value={cif?.category_code}
                        onChange={(v) => updateCif({ category_code: v })}
                      />
                      <ExtractRow
                        label="Établissement secondaire"
                        value={cif?.secondary_establishment}
                        onChange={(v) => updateCif({ secondary_establishment: v })}
                      />
                      <ExtractRow
                        label="Nom / raison sociale"
                        value={cif?.name}
                        onChange={(v) => updateCif({ name: v })}
                      />
                      <ExtractRow
                        label="Activité principale"
                        value={cif?.main_activity}
                        onChange={(v) => updateCif({ main_activity: v })}
                      />
                      <ExtractRow
                        label="Adresse"
                        value={cif?.address}
                        onChange={(v) => updateCif({ address: v })}
                      />
                      <ExtractRow
                        label="Statut TVA (carte)"
                        value={cif?.vat_status}
                        onChange={(v) => updateCif({ vat_status: v })}
                      />
                    </div>
                    <p className="extract-conf">
                      Confiance : {cif ? `${(cif.confidence * 100).toFixed(0)}%` : '—'}
                    </p>
                  </div>

                  <div className="block">
                    <h3>Extrait RNE</h3>
                    <div className="extract-list">
                      <ExtractRow
                        label="Identifiant RNE"
                        value={rne?.rne_identifier}
                        onChange={(v) => updateRne({ rne_identifier: v })}
                      />
                      <ExtractRow
                        label="Forme juridique"
                        value={rne?.legal_form}
                        onChange={(v) => updateRne({ legal_form: v })}
                      />
                      <ExtractRow
                        label="Dénomination"
                        value={rne?.company_name}
                        onChange={(v) => updateRne({ company_name: v })}
                      />
                      <ExtractRow
                        label="Nom commercial"
                        value={rne?.commercial_name_latin || rne?.commercial_name}
                        onChange={(v) => updateRne({ commercial_name_latin: v, commercial_name: v })}
                      />
                      <ExtractRow
                        label="Capital"
                        value={rne?.capital}
                        onChange={(v) =>
                          updateRne({
                            capital: v.trim() === '' ? null : Number(v.replace(/[^\d.]/g, '')) || null,
                          })
                        }
                      />
                      <ExtractRow
                        label="Adresse (siège)"
                        value={rne?.registered_address}
                        onChange={(v) => updateRne({ registered_address: v })}
                      />
                      <ExtractRow
                        label="Activité"
                        value={rne?.main_activity}
                        onChange={(v) => updateRne({ main_activity: v })}
                      />
                      <ExtractRow
                        label="Date d’immatriculation"
                        value={rne?.registration_date}
                        onChange={(v) => updateRne({ registration_date: v })}
                      />
                    </div>
                    <p className="extract-conf">
                      Confiance : {rne ? `${(rne.confidence * 100).toFixed(0)}%` : '—'}
                    </p>
                  </div>
                </div>

                {(cif?.warnings?.length || rne?.warnings?.length) && (
                  <div className="warn-list">
                    <h3>À vérifier</h3>
                    <ul>
                      {(cif?.warnings || []).map((w, i) => (
                        <li key={`cif-${i}`}>CIF : {w}</li>
                      ))}
                      {(rne?.warnings || []).map((w, i) => (
                        <li key={`rne-${i}`}>RNE : {w}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={() => {
                      const next = buildProfileFromDocs(cif, rne)
                      void persistProfile(next)
                      setQIndex(0)
                      setStep(1)
                    }}
                  >
                    Confirmer et continuer
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => setStep(4)}
                  >
                    Corriger le profil
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => setStep(3)}
                  >
                    Modifier les documents
                  </button>
                </div>
              </section>
            )}

            {/* —— 4. PROFIL —— */}
            {step === 4 && (
              <section className="panel" data-spotlight="profile">
                <h2>Profil entreprise</h2>
                <p className="sub">
                  Vérifiez les champs extraits — corrigez notamment la forme juridique si besoin.
                </p>
                <div className="profile-card">
                  <div className="grid-2">
                    <div className="field">
                      <label>Raison sociale / Nom</label>
                      <input
                        value={profileDraft.name}
                        onChange={(e) =>
                          setProfileDraft({ ...profileDraft, name: e.target.value })
                        }
                      />
                    </div>
                    <div className="field">
                      <label>Matricule fiscal</label>
                      <input
                        value={profileDraft.tax_id}
                        onChange={(e) =>
                          setProfileDraft({ ...profileDraft, tax_id: e.target.value })
                        }
                      />
                    </div>
                    <div className="field">
                      <label>Code TVA</label>
                      <input
                        value={profileDraft.vat_code}
                        onChange={(e) =>
                          setProfileDraft({ ...profileDraft, vat_code: e.target.value })
                        }
                      />
                    </div>
                    <div className="field">
                      <label>Code catégorie</label>
                      <input
                        value={profileDraft.category_code}
                        onChange={(e) =>
                          setProfileDraft({ ...profileDraft, category_code: e.target.value })
                        }
                      />
                    </div>
                    <div className="field">
                      <label>Identifiant RNE</label>
                      <input
                        value={profileDraft.rne_identifier}
                        onChange={(e) =>
                          setProfileDraft({ ...profileDraft, rne_identifier: e.target.value })
                        }
                      />
                    </div>
                    <div className="field">
                      <label>Nom commercial</label>
                      <input
                        value={profileDraft.commercial_name}
                        onChange={(e) =>
                          setProfileDraft({ ...profileDraft, commercial_name: e.target.value })
                        }
                      />
                    </div>
                  </div>
                  <div className="field">
                    <label>Adresse</label>
                    <input
                      value={profileDraft.address}
                      onChange={(e) =>
                        setProfileDraft({ ...profileDraft, address: e.target.value })
                      }
                    />
                  </div>
                  <div className="field">
                    <label>Activité</label>
                    <input
                      value={profileDraft.activity}
                      onChange={(e) =>
                        setProfileDraft({ ...profileDraft, activity: e.target.value })
                      }
                    />
                  </div>
                  <div className="grid-2">
                    <div className="field">
                      <label>Forme juridique</label>
                      <select
                        value={(() => {
                          const cur = profileDraft.legal_form.trim()
                          const byLabel = LEGAL_FORMS.find((f) => f.label === cur)
                          if (byLabel) return byLabel.label
                          const byCode = LEGAL_FORMS.find((f) =>
                            cur.toUpperCase().startsWith(f.code),
                          )
                          return byCode?.label || ''
                        })()}
                        onChange={(e) =>
                          setProfileDraft({ ...profileDraft, legal_form: e.target.value })
                        }
                      >
                        <option value="">Choisir (extrait RNE)…</option>
                        {LEGAL_FORMS.map((f) => (
                          <option key={f.code} value={f.label}>
                            {f.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="field">
                      <label>Statut TVA (carte)</label>
                      <input
                        value={profileDraft.vat_status}
                        onChange={(e) =>
                          setProfileDraft({ ...profileDraft, vat_status: e.target.value })
                        }
                      />
                    </div>
                  </div>
                  <div className="grid-2">
                    <div className="field">
                      <label>Mois</label>
                      <input
                        type="number"
                        min={1}
                        max={12}
                        value={month}
                        onChange={(e) => setMonth(Number(e.target.value))}
                      />
                    </div>
                    <div className="field">
                      <label>Année</label>
                      <input
                        type="number"
                        value={year}
                        onChange={(e) => setYear(Number(e.target.value))}
                      />
                    </div>
                  </div>
                </div>
                <div className="actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={!profileDraft.tax_id.trim() || !profileDraft.name.trim() || busyProfile}
                    onClick={() => {
                      void persistProfile().then(() => setStep(5))
                    }}
                  >
                    Accéder aux factures (Fatoora)
                  </button>
                  <button type="button" className="btn btn-ghost" onClick={() => setStep(3)}>
                    Rescanner
                  </button>
                </div>
              </section>
            )}

            {/* —— 5. FATOORA TEIF XML —— */}
            {step === 5 && (
              <section className="panel" data-spotlight="invoices">
                <h2>Fatoora — factures TEIF</h2>
                <p className="sub">
                  Importez le fichier <strong>XML TEIF</strong> exporté depuis El Fatoora / TTN.
                  Tasrih lit HT, TVA, TTC, timbre et lignes, puis remplit la déclaration mensuelle.
                </p>
                <label className={`scan-zone${busy ? ' busy' : ''}`} style={{ marginTop: '0.75rem' }}>
                  <input
                    type="file"
                    accept=".xml,.xlms,application/xml,text/xml"
                    multiple
                    disabled={busy}
                    onChange={(e) => void onInvoices(e.target.files)}
                  />
                  <div className="pulse">XML</div>
                  <strong>{busy ? 'Lecture TEIF…' : 'Déposer le fichier Fatoora (XML)'}</strong>
                  <p>TEIF_FAC-….xml — un ou plusieurs fichiers</p>
                </label>
                {invoices.length > 0 && (
                  <ul className="inv-list">
                    {invoices.map((inv, i) => (
                      <li key={`${inv.filename}-${i}`}>
                        <strong>{inv.invoice_number || inv.filename}</strong>
                        <span>
                          {inv.vendor || '—'} · HT {inv.amount_ht ?? '—'} · TVA{' '}
                          {inv.vat_amount ?? '—'} · TTC {inv.amount_ttc ?? '—'} · Timbre{' '}
                          {inv.stamp_duty ?? '—'}
                        </span>
                        {inv.category_guess === 'teif_xml' && (
                          <span className="ok-pill" style={{ marginTop: '0.35rem' }}>
                            TEIF XML extrait
                          </span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
                <div className="actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busy}
                    onClick={() => setStep(7)}
                  >
                    Continuer vers la retenue (TEJ)
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    disabled={busy}
                    onClick={() => {
                      setInvoices([])
                      setFilled(null)
                    }}
                  >
                    Vider
                  </button>
                  <button type="button" className="btn btn-ghost" onClick={() => setStep(4)}>
                    Retour profil
                  </button>
                </div>
              </section>
            )}

            {/* —— 7. RETENUE À LA SOURCE (TEJ) —— */}
            {step === 7 && (
              <section className="panel" data-spotlight="tej">
                <h2>Retenue à la source — TEJ</h2>
                <p className="sub">
                  Exportez votre déclaration de retenue à la source au format XML depuis le
                  portail <strong>TEJ</strong> (Tunisie TradeNet), puis importez-la ici. Tasrih
                  remplit le tableau officiel « Retenue à la source » (جدول الخصم من المورد).
                </p>

                <div className="tej-grid">
                  <div className="block">
                    <h4>1. Portail TEJ</h4>
                    <p className="sub" style={{ margin: '0.35rem 0 0.5rem' }}>
                      Connectez-vous à TEJ, déclarez la retenue à la source, puis téléchargez le
                      fichier <strong>XML</strong> de la déclaration.
                    </p>
                    <a
                      className="btn btn-primary"
                      href="https://tej.finances.gov.tn/"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Ouvrir tej.finances.gov.tn ↗
                    </a>
                  </div>
                  <label
                    className={`scan-zone compact${busyRetenue ? ' busy' : ''}`}
                    style={{ display: 'block' }}
                  >
                    <input
                      type="file"
                      accept=".xml,.xlms,application/xml,text/xml"
                      multiple
                      disabled={busyRetenue}
                      onChange={(e) => void onRetenues(e.target.files)}
                    />
                    <strong>
                      {busyRetenue ? 'Lecture du XML…' : '2. Importer le XML TEJ'}
                    </strong>
                    <p>Déclaration de retenue (DeclarationsRS) — un ou plusieurs fichiers</p>
                  </label>
                </div>

                {retenues.length > 0 && (
                  <ul className="inv-list">
                    {retenues.map((r, i) => (
                      <li key={`${r.certificate_number || 'ret'}-${i}`}>
                        <strong>{r.beneficiary || r.certificate_number || 'Bénéficiaire'}</strong>
                        <span>
                          {r.beneficiary_tax_id || '—'} · {r.nature || '—'} · Base{' '}
                          {r.base} · Taux {r.rate ?? '—'}% · Retenue {r.amount} TND
                        </span>
                      </li>
                    ))}
                  </ul>
                )}

                {retenueDecls.length > 0 && (
                  <p className="ok-pill">
                    {retenueDecls.length} déclaration(s) TEJ · total retenue{' '}
                    {retenueDecls.reduce((s, d) => s + d.total_rs, 0).toFixed(3)} TND · période{' '}
                    {retenueDecls[0].month ?? '—'}/{retenueDecls[0].year ?? '—'}
                  </p>
                )}

                <div className="actions">
                  <button
                    type="button"
                    className="btn btn-primary"
                    disabled={busy || retenueDecls.length === 0}
                    onClick={() => void exportRetenuePdf()}
                  >
                    {busy ? 'Génération…' : 'Générer le PDF « Retenue à la source »'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    disabled={busy}
                    onClick={() => void runPipeline()}
                  >
                    Remplir la déclaration mensuelle
                  </button>
                  <button type="button" className="btn btn-ghost" onClick={() => setStep(5)}>
                    Retour factures
                  </button>
                </div>
                <p className="foot-note">
                  Pas de retenue ce mois-ci ? Continuez directement vers la déclaration
                  mensuelle.
                </p>
              </section>
            )}

            {/* —— 6. FORMULAIRE —— */}
            {step === 6 && filled && (
              <section className="panel" data-spotlight="form">
                <h2>Déclaration mensuelle</h2>
                <p className="sub">
                  {filled.profile.name} · {filled.profile.tax_id}
                  {filled.profile.legal_form ? ` · ${filled.profile.legal_form}` : ''} · confiance{' '}
                  {(filled.confidence * 100).toFixed(0)}%
                </p>
                <div className="meter">
                  <span style={{ width: `${Math.round(filled.confidence * 100)}%` }} />
                </div>

                <div className="gaps">
                  <h3>Avant d’ouvrir le formulaire</h3>
                  <div className="gap-item">
                    <p>Avez-vous effectué des retenues à la source ?</p>
                    <div className="gap-opts">
                      <button
                        type="button"
                        className={
                          answers.does_withholding === true ? 'btn btn-primary' : 'btn btn-ghost'
                        }
                        onClick={() =>
                          setAnswers((a) => ({ ...a, does_withholding: true }))
                        }
                      >
                        Oui
                      </button>
                      <button
                        type="button"
                        className={
                          answers.does_withholding === false ? 'btn btn-primary' : 'btn btn-ghost'
                        }
                        onClick={() =>
                          setAnswers((a) => ({ ...a, does_withholding: false }))
                        }
                      >
                        Non
                      </button>
                    </div>
                  </div>
                  {filled.gap_questions
                    .filter((g) => g.field !== 'does_withholding')
                    .map((g) => (
                      <div className="gap-item" key={g.id}>
                        <p>{g.question_fr}</p>
                        <div className="gap-opts">
                          {g.options.map((opt) => (
                            <button
                              key={String(opt.value)}
                              type="button"
                              className={
                                answers[g.field] === opt.value
                                  ? 'btn btn-primary'
                                  : 'btn btn-ghost'
                              }
                              disabled={busy}
                              onClick={() => answerGap(g.field, opt.value)}
                            >
                              {opt.label}
                            </button>
                          ))}
                        </div>
                      </div>
                    ))}
                  {answers.does_withholding !== undefined && (
                    <button
                      type="button"
                      className="btn btn-ghost"
                      disabled={busy}
                      onClick={() => void runPipeline()}
                    >
                      Recalculer avec la réponse
                    </button>
                  )}
                </div>

                {filled.needs_user_review.length > 0 && (
                  <div className="warn-list">
                    <h3>À vérifier</h3>
                    <ul>
                      {filled.needs_user_review.map((w) => (
                        <li key={w}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <div className="result-grid">
                  <div className="block">
                    <h3>Montants pour la déclaration</h3>
                    <ul>
                      <li>CA HT total : {filled.amounts.ca_ht} TND</li>
                      {filled.amounts.ca_ht_19 > 0 &&
                        Math.abs(filled.amounts.ca_ht_19 - filled.amounts.ca_ht) > 0.001 && (
                          <li>Base TVA 19% : {filled.amounts.ca_ht_19} TND</li>
                        )}
                      {filled.amounts.ca_ht_13 > 0 && (
                        <li>Base TVA 13% : {filled.amounts.ca_ht_13} TND</li>
                      )}
                      {filled.amounts.ca_ht_7 > 0 && (
                        <li>Base TVA 7% : {filled.amounts.ca_ht_7} TND</li>
                      )}
                      {filled.amounts.tva_collectee_19 > 0 && (
                        <li>TVA 19% : {filled.amounts.tva_collectee_19} TND</li>
                      )}
                      {filled.amounts.tva_deductible > 0 && (
                        <li>TVA déductible : {filled.amounts.tva_deductible} TND</li>
                      )}
                      <li>TVA nette due : {filled.amounts.tva_nette} TND</li>
                      {filled.amounts.tva_credit_next > 0 && (
                        <li>Crédit TVA à reporter : {filled.amounts.tva_credit_next} TND</li>
                      )}
                      {filled.amounts.retenues_total > 0 && (
                        <li>Retenue à la source : {filled.amounts.retenues_total} TND</li>
                      )}
                      {filled.amounts.masse_salariale_brute > 0 && (
                        <li>Masse salariale brute : {filled.amounts.masse_salariale_brute} TND</li>
                      )}
                      {filled.amounts.tfp_amount > 0 && (
                        <li>
                          TFP : {filled.amounts.tfp_amount} TND ({(filled.amounts.tfp_rate * 100).toFixed(0)}%)
                        </li>
                      )}
                      {filled.amounts.foprolos_amount > 0 && (
                        <li>FOPROLOS : {filled.amounts.foprolos_amount} TND</li>
                      )}
                      {filled.amounts.stamp_duty_total > 0 && (
                        <li>
                          Timbre fiscal : {filled.amounts.stamp_duty_total} TND (
                          {filled.amounts.stamp_duty_count} facture(s) encaissée(s))
                        </li>
                      )}
                      {filled.amounts.etablissement_tax_amount > 0 && (
                        <li>
                          معلوم مؤسسات : {filled.amounts.etablissement_tax_amount} TND
                        </li>
                      )}
                      {filled.amounts.hotel_tax_amount > 0 && (
                        <li>معلوم نزل : {filled.amounts.hotel_tax_amount} TND</li>
                      )}
                    </ul>
                  </div>
                  <div className="block">
                    <h3>Cases cochées</h3>
                    <ul>
                      {Object.entries(filled.checkboxes)
                        .filter(([, v]) => v)
                        .map(([k]) => (
                          <li key={k}>[x] {k}</li>
                        ))}
                      {Object.values(filled.checkboxes).every((v) => !v) && (
                        <li>Aucune</li>
                      )}
                    </ul>
                  </div>
                  <div className="block">
                    <h3>Taxes applicables / sans objet</h3>
                    <p className="sub" style={{ margin: '0 0 0.5rem' }}>
                      Domaine d’activité : <strong>{filled.domain || '—'}</strong>
                    </p>
                    <ul className="tax-list">
                      {(filled.tax_lines || []).map((t) => (
                        <li key={t.key} className={t.applicable ? '' : 'na-line'}>
                          <span className={t.applicable ? 'tag-on' : 'tag-na'}>
                            {t.applicable ? '✓' : 'X'}
                          </span>{' '}
                          <span>
                            {t.label_fr}
                            {!t.applicable && <em> — sans objet</em>}
                          </span>
                        </li>
                      ))}
                      {(!filled.tax_lines || filled.tax_lines.length === 0) && (
                        <li>—</li>
                      )}
                    </ul>
                  </div>
                </div>

                <section className="panel" data-spotlight="amounts">
                  <h3>Rubriques à remplir</h3>
                  <p className="sub">
                    Les valeurs proposées viennent des factures TEIF, des certificats TEJ et des
                    fiches de paie. Corrigez-les si besoin puis appliquez le recalcul.
                  </p>

                  {/* 1. Retenue à la source */}
                  <div className="block">
                    <h4>1. Retenue à la source (certificats TEJ)</h4>
                    <label className={`scan-zone${busyRetenue ? ' busy' : ''}`}>
                      <input
                        type="file"
                        accept=".xml,.xlms"
                        multiple
                        disabled={busyRetenue}
                        onChange={(e) => void onRetenues(e.target.files)}
                      />
                      <strong>
                        {busyRetenue
                          ? 'Lecture du XML…'
                          : 'Importer les certificats de retenue (XML TEJ)'}
                      </strong>
                    </label>
                    {retenues.length > 0 && (
                      <ul className="inv-list">
                        {retenues.map((r, i) => (
                          <li key={`${r.certificate_number || 'ret'}-${i}`}>
                            <strong>{r.beneficiary || r.certificate_number || 'Certificat'}</strong>
                            <span>
                              Base {r.base} · Taux {r.rate ?? '—'} · Montant {r.amount} TND
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                    <AmountRow
                      label="Total retenues (TND)"
                      field="retenues_total"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                  </div>

                  {/* 2-3. TFP & FOPROLOS */}
                  <div className="block">
                    <h4>2-3. TFP &amp; FOPROLOS (masse salariale brute)</h4>
                    <button
                      type="button"
                      className="btn btn-ghost"
                      disabled={busyPayroll}
                      onClick={() => void loadPayroll()}
                    >
                      {busyPayroll
                        ? 'Lecture des fiches de paie…'
                        : 'Calculer depuis les fiches de paie scannées'}
                    </button>
                    {payslips.length > 0 && (
                      <p className="sub">
                        {payslips.length} fiche(s) de paie · masse brute cumulée sur la
                        déclaration : {filled.amounts.masse_salariale_brute} TND
                      </p>
                    )}
                    <AmountRow
                      label="Masse salariale brute (TND)"
                      field="masse_salariale_brute"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="TFP — assiette (TND)"
                      field="tfp_base"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="TFP — taux en fraction (0.01 manufacture / 0.02 autres)"
                      field="tfp_rate"
                      step="0.001"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="TFP — montant (TND)"
                      field="tfp_amount"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="FOPROLOS — assiette (TND)"
                      field="foprolos_base"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="FOPROLOS — montant (1%)"
                      field="foprolos_amount"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                  </div>

                  {/* 4. TVA */}
                  <div className="block">
                    <h4>4. TVA collectée / déductible</h4>
                    <AmountRow
                      label="CA HT 7%"
                      field="ca_ht_7"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="CA HT 13%"
                      field="ca_ht_13"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="CA HT 19%"
                      field="ca_ht_19"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="TVA collectée (TND)"
                      field="tva_collectee"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="TVA déductible (achats)"
                      field="tva_deductible"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="Crédit TVA reporté (mois précédent)"
                      field="tva_credit_report"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="TVA nette due (TND)"
                      field="tva_nette"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="Crédit TVA à reporter"
                      field="tva_credit_next"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                  </div>

                  {/* 6. Droit de timbre */}
                  <div className="block">
                    <h4>6. Droit de timbre fiscal (1 DT / facture encaissée)</h4>
                    <AmountRow
                      label="Nombre de factures encaissées"
                      field="stamp_duty_count"
                      step="1"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="Droit de timbre total (TND)"
                      field="stamp_duty_total"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                  </div>

                  {/* 7. Taxe hôtelière */}
                  <div className="block">
                    <h4>7. Taxe hôtelière (2%)</h4>
                    <AmountRow
                      label="CA brut établissement hôtelier"
                      field="hotel_tax_base"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                    <AmountRow
                      label="Montant taxe hôtelière (TND)"
                      field="hotel_tax_amount"
                      amounts={filled.amounts as unknown as Record<string, number>}
                      edits={amountEdits}
                      onEdit={editAmount}
                    />
                  </div>

                  {materialOverrides.length > 0 && (
                    <div className="block">
                      <h4>Motifs des corrections (obligatoire — DGI)</h4>
                      <p className="sub">
                        Toute modification d’une valeur matérielle au-delà de{' '}
                        {OVERRIDE_TOLERANCE_PCT} % doit être justifiée. Ces motifs sont
                        transmis à l’administration fiscale.
                      </p>
                      {materialOverrides.map((o) => (
                        <div className="override-row" key={o.field}>
                          <strong>{o.label}</strong>
                          <span>
                            Extrait {o.ocr} → saisi {o.manual} ({o.delta > 0 ? '+' : ''}
                            {o.delta.toFixed(1)} %)
                          </span>
                          <input
                            placeholder="Motif (obligatoire)"
                            value={fieldComments[o.field] ?? ''}
                            onChange={(e) =>
                              setFieldComments((p) => ({ ...p, [o.field]: e.target.value }))
                            }
                            className={
                              !(fieldComments[o.field] || '').trim() ? 'need-comment' : ''
                            }
                          />
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="actions">
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={busy || !hasAmountEdits}
                      onClick={() => void runPipeline()}
                    >
                      {busy ? 'Recalcul…' : 'Appliquer et recalculer'}
                    </button>
                    {hasAmountEdits && (
                      <button
                        type="button"
                        className="btn btn-ghost"
                        disabled={busy}
                        onClick={() => setAmountEdits({})}
                      >
                        Annuler mes modifications
                      </button>
                    )}
                  </div>
                </section>

                <form className="actions" onSubmit={(e) => void openOfficialPdf(e)}>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={busy || answers.does_withholding === undefined}
                  >
                    {busy ? 'Génération…' : 'Générer le PDF — Déclaration mensuelle'}
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    disabled={busy}
                    onClick={() => setStep(7)}
                  >
                    Retour retenue (TEJ)
                  </button>
                </form>
                <p className="foot-note">
                  Génère le formulaire officiel (12 pages) prérempli avec vos données, puis le
                  télécharge. Vérifiez les montants avant dépôt.
                </p>
              </section>
            )}
          </>
        )}
      </div>

      {showAuth && !loggedIn && (
        <div className="auth-modal" role="dialog" aria-modal="true">
          <div
            className="auth-modal-backdrop"
            onClick={() => setShowAuth(false)}
            aria-hidden="true"
          />
          <div className="auth-modal-card">
            <button
              type="button"
              className="auth-modal-close"
              aria-label={t('Fermer')}
              onClick={() => setShowAuth(false)}
            >
              ×
            </button>
            <h2 className="auth-title">
              {authMode === 'register' ? t('Créer mon compte') : t('Se connecter')}
            </h2>
            <p className="auth-sub">
              {t('Accédez à votre espace pour préparer votre déclaration mensuelle.')}
            </p>
            <form className="auth-card" onSubmit={(e) => void submitAuth(e)}>
              <div className="auth-tabs">
                <button
                  type="button"
                  className={authMode === 'register' ? 'on' : ''}
                  onClick={() => setAuthMode('register')}
                >
                  {t("S'inscrire")}
                </button>
                <button
                  type="button"
                  className={authMode === 'login' ? 'on' : ''}
                  onClick={() => setAuthMode('login')}
                >
                  {t('Se connecter')}
                </button>
              </div>
              <div className="field">
                <label htmlFor="email">{t('Email')}</label>
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={authForm.email}
                  onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })}
                />
              </div>
              <div className="field">
                <label htmlFor="password">{t('Mot de passe')}</label>
                <input
                  id="password"
                  type="password"
                  required
                  minLength={6}
                  autoComplete={authMode === 'register' ? 'new-password' : 'current-password'}
                  value={authForm.password}
                  onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })}
                />
              </div>
              {authMode === 'register' && (
                <div className="field">
                  <label htmlFor="phone">{t('Numéro de téléphone')}</label>
                  <input
                    id="phone"
                    type="tel"
                    required
                    autoComplete="tel"
                    placeholder="+216 …"
                    value={authForm.phone}
                    onChange={(e) => setAuthForm({ ...authForm, phone: e.target.value })}
                  />
                </div>
              )}
              {error && <p className="error">{error}</p>}
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy
                  ? t('Patientez…')
                  : authMode === 'register'
                    ? t("S'inscrire et continuer")
                    : t('Se connecter')}
              </button>
            </form>
          </div>
        </div>
      )}

      <AssistantWidget
        step={agentStep}
        qIndex={agentStep === 1 ? qIndex : null}
        context={agentContext}
        onHighlight={setSpotlight}
      />
    </div>
  )
}
