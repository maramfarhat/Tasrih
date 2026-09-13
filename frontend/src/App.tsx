import { FormEvent, useEffect, useMemo, useState } from 'react'

const API = import.meta.env.VITE_API_URL || '/api'
const TOKEN_KEY = 'tasrih_token'

type User = { id: number; email: string; phone: string }

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
    tva_deductible: number
    tva_nette: number
    stamp_duty_total: number
    etablissement_tax_base: number
    etablissement_tax_amount: number
    hotel_tax_base: number
    hotel_tax_amount: number
  }
  checkboxes: Record<string, boolean>
  gap_questions: Gap[]
  confidence: number
  needs_user_review: string[]
  checklist: string[]
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

/** After login: questions → (employees) → scan → profil → factures → formulaire */
const STEPS = ['Questions', 'Docs', 'Scan', 'Profil', 'Factures', 'Formulaire'] as const

function authHeaders(token: string | null): HeadersInit {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export default function App() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<User | null>(null)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('register')
  const [authForm, setAuthForm] = useState({ email: '', password: '', phone: '' })
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
  const [busyEmp, setBusyEmp] = useState(false)

  const [cif, setCif] = useState<CIF | null>(null)
  const [rne, setRne] = useState<RNE | null>(null)
  const [busyCif, setBusyCif] = useState(false)
  const [busyRne, setBusyRne] = useState(false)
  const [profileDraft, setProfileDraft] = useState({
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
  })
  const [invoices, setInvoices] = useState<Invoice[]>([])
  const [month, setMonth] = useState(new Date().getMonth() + 1)
  const [year, setYear] = useState(new Date().getFullYear())
  const [answers, setAnswers] = useState<Record<string, unknown>>({})
  const [filled, setFilled] = useState<Filled | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const loggedIn = Boolean(token && user)

  const payload = useMemo(
    () => ({
      month: { year, month, declaration_code: '0' },
      cif,
      rne,
      invoices,
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
    [year, month, cif, rne, invoices, answers, profileDraft, onboarding.has_personnel],
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
        if (data.onboarding?.previous_is != null) {
          setOnboarding({
            previous_is: data.onboarding.previous_is || '',
            has_personnel: data.onboarding.has_personnel ?? null,
            declaration_channel: data.onboarding.declaration_channel || '',
            accountant_manages: data.onboarding.accountant_manages ?? null,
          })
        }
        setEmployees(data.employees || [])
        if (data.onboarding?.declaration_channel) {
          setStep(3)
        } else {
          setQIndex(0)
          setStep(1)
        }
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
      setStep(1)
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
    setStep(0)
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
        setStep(3)
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
    if (!empContract && !empCnss) {
      setError('Ajoutez le contrat de travail et/ou la fiche CNSS')
      return
    }
    setBusyEmp(true)
    setError(null)
    try {
      const fd = new FormData()
      fd.append('employee_name', empName.trim())
      if (empContract) fd.append('contract', empContract)
      if (empCnss) fd.append('cnss', empCnss)
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
    if (!res.ok) throw new Error(await res.text())
    return res.json()
  }

  function buildProfileFromDocs(nextCif: CIF | null, nextRne: RNE | null) {
    setProfileDraft({
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
    })
  }

  async function onCif(files: FileList | null, input: HTMLInputElement) {
    if (!files?.[0]) return
    setBusyCif(true)
    setError(null)
    try {
      const data = await uploadExtract('cif', files[0])
      setCif(data)
      buildProfileFromDocs(data, rne)
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
      buildProfileFromDocs(cif, data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur RNE')
    } finally {
      setBusyRne(false)
      input.value = ''
    }
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

  async function runPipeline() {
    setBusy(true)
    setError(null)
    try {
      const res = await fetch(`${API}/pipeline/build`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
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

  async function openOfficialPdf(e: FormEvent) {
    e.preventDefault()
    if (answers.does_withholding === undefined) {
      setError('Répondez à la question sur les retenues à la source')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const res = await fetch(`${API}/pipeline/export-official`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!res.ok) throw new Error(await res.text())
      const buf = await res.arrayBuffer()
      if (!buf.byteLength) throw new Error('PDF vide')
      const url = URL.createObjectURL(new Blob([buf], { type: 'application/pdf' }))
      window.open(url, '_blank', 'noopener,noreferrer')
      window.setTimeout(() => URL.revokeObjectURL(url), 120_000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export échoué')
    } finally {
      setBusy(false)
    }
  }

  const progressIndex =
    step === 1 ? 0 : step === 2 ? 1 : step === 3 ? 2 : step === 4 ? 3 : step === 5 ? 4 : step === 6 ? 5 : -1

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
      <div className="shell">
        {/* —— HOME + AUTH —— */}
        {!loggedIn && (
          <section className="hero home-auth">
            <div className="brand-lockup">
              <img src="/favicon.svg" alt="" className="brand-logo" width={72} height={72} />
              <h1 className="brand">
                <span>Déclaration mensuelle Tunisie</span>
                Tasrih
              </h1>
            </div>
            <p className="lead">
              Créez votre compte, répondez aux questions, scannez vos documents et générez votre
              déclaration mensuelle.
            </p>

            <form className="auth-card" onSubmit={(e) => void submitAuth(e)}>
              <div className="auth-tabs">
                <button
                  type="button"
                  className={authMode === 'register' ? 'on' : ''}
                  onClick={() => setAuthMode('register')}
                >
                  Créer un compte
                </button>
                <button
                  type="button"
                  className={authMode === 'login' ? 'on' : ''}
                  onClick={() => setAuthMode('login')}
                >
                  Se connecter
                </button>
              </div>
              <div className="field">
                <label htmlFor="email">Email</label>
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
                <label htmlFor="password">Mot de passe</label>
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
                  <label htmlFor="phone">Numéro de téléphone</label>
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
                  ? 'Patientez…'
                  : authMode === 'register'
                    ? 'S’inscrire et continuer'
                    : 'Se connecter'}
              </button>
            </form>
          </section>
        )}

        {loggedIn && (
          <>
            <header className="topbar">
              <div className="logo-row">
                <img src="/favicon.svg" alt="" className="logo-mark" width={28} height={28} />
                <p className="logo-mini">Tasrih</p>
              </div>
              <div className="progress">
                {STEPS.map((label, i) => (
                  <i
                    key={label}
                    className={progressIndex === i ? 'on' : progressIndex > i ? 'done' : ''}
                    title={label}
                  />
                ))}
              </div>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => void logout()}>
                {user?.email}
              </button>
            </header>

            {error && <p className="error">{error}</p>}

            {/* —— 1. QUESTIONS (one screen each) —— */}
            {step === 1 && qIndex === 0 && (
              <section className="panel question-screen">
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
              <section className="panel question-screen">
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
              <section className="panel question-screen">
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
              <section className="panel question-screen">
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
              <section className="panel">
                <h2>Documents du personnel</h2>
                <p className="sub">
                  Pour chaque employé, déposez le <strong>contrat de travail</strong> et la{' '}
                  <strong>fiche CNSS</strong>.
                </p>
                <form className="profile-card" onSubmit={(e) => void uploadEmployee(e)}>
                  <div className="field">
                    <label>Nom de l’employé</label>
                    <input value={empName} onChange={(e) => setEmpName(e.target.value)} />
                  </div>
                  <div className="grid-2">
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
                    <label className={`scan-zone compact${busyEmp ? ' busy' : ''}`}>
                      <input
                        type="file"
                        accept=".pdf,image/*"
                        disabled={busyEmp}
                        onChange={(e) => setEmpCnss(e.target.files?.[0] || null)}
                      />
                      <strong>{empCnss ? empCnss.name : 'Fiche CNSS'}</strong>
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
                          {emp.has_cnss ? 'OK' : '—'}
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
              <section className="panel">
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
                      setStep(4)
                    }}
                  >
                    Voir le profil entreprise
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    onClick={() => setStep(onboarding.has_personnel ? 2 : 1)}
                  >
                    Retour
                  </button>
                </div>
              </section>
            )}

            {/* —— 4. PROFIL —— */}
            {step === 4 && (
              <section className="panel">
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
                    disabled={!profileDraft.tax_id.trim() || !profileDraft.name.trim()}
                    onClick={() => setStep(5)}
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
              <section className="panel">
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
                    disabled={busy || invoices.length === 0}
                    onClick={() => void runPipeline()}
                  >
                    {busy ? 'Calcul…' : 'Remplir la déclaration mensuelle'}
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

            {/* —— 6. FORMULAIRE —— */}
            {step === 6 && filled && (
              <section className="panel">
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
                      {filled.amounts.stamp_duty_total > 0 && (
                        <li>Timbre fiscal : {filled.amounts.stamp_duty_total} TND</li>
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
                </div>

                <form className="actions" onSubmit={(e) => void openOfficialPdf(e)}>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={busy || answers.does_withholding === undefined}
                  >
                    Réouvrir la déclaration mensuelle
                  </button>
                  <button
                    type="button"
                    className="btn btn-ghost"
                    disabled={busy}
                    onClick={() => setStep(5)}
                  >
                    Retour factures
                  </button>
                </form>
                <p className="foot-note">
                  PDF = mensuelle2026 officiel (12 pages) prérempli. Ctrl+S pour enregistrer.
                  Vérifiez avant dépôt.
                </p>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  )
}
