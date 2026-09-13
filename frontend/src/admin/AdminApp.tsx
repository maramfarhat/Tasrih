import { FormEvent, useCallback, useEffect, useState, type ReactElement } from 'react'
import './admin.css'

/**
 * Vue administration DGI — totalement séparée de l'interface contribuable.
 * Accessible via /admin (l'admin ne doit jamais être visible côté contribuable).
 *
 * Toute règle affichée montre les chiffres exacts + une explication en clair
 * (pas de score opaque).
 */

const API = import.meta.env.VITE_API_URL || '/api'
const KEY_STORAGE = 'tasrih_admin_key'

type Severity = 'low' | 'medium' | 'high'

const SEV_COLOR: Record<Severity, string> = {
  high: '#dc3545',
  medium: '#fd7e14',
  low: '#ffc107',
}
const SEV_LABEL: Record<Severity, string> = {
  high: 'Élevé',
  medium: 'Moyen',
  low: 'Faible',
}
const FLAG_LABEL: Record<string, string> = {
  manual_override: 'Correction manuelle',
  revenue_mismatch: 'Écart CA / facturation',
  sudden_drop: 'Chute brutale',
}

function money(v: unknown): string {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return `${n.toLocaleString('fr-FR', { minimumFractionDigits: 3, maximumFractionDigits: 3 })} TND`
}

async function adminFetch<T>(path: string, key: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', 'X-Admin-Key': key, ...(init?.headers || {}) },
  })
  if (res.status === 401) throw new Error('unauthorized')
  if (!res.ok) throw new Error(await res.text())
  return (await res.json()) as T
}

function SeverityDot({ severity }: { severity?: Severity | null }) {
  const color = severity ? SEV_COLOR[severity] : '#adb5bd'
  return <span className="ad-dot" style={{ background: color }} title={severity ?? 'aucun'} />
}

function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span className="ad-badge" style={{ background: SEV_COLOR[severity] }}>
      {SEV_LABEL[severity]}
    </span>
  )
}

// ————————————————————————— Login —————————————————————————

function AdminLogin({ onOk }: { onOk: (key: string) => void }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const res = await fetch(`${API}/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      })
      if (!res.ok) throw new Error('Mot de passe incorrect')
      localStorage.setItem(KEY_STORAGE, password)
      onOk(password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="ad-login">
      <form className="ad-login-card" onSubmit={(e) => void submit(e)}>
        <div className="ad-login-flag">🇹🇳</div>
        <h1>Administration DGI</h1>
        <p>Espace réservé à l'administration fiscale — suivi &amp; contrôle.</p>
        <label>
          Mot de passe administrateur
          <input
            type="password"
            value={password}
            autoFocus
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error && <p className="ad-error">{error}</p>}
        <button type="submit" className="ad-btn ad-btn-primary" disabled={busy || !password}>
          {busy ? 'Connexion…' : 'Se connecter'}
        </button>
      </form>
    </div>
  )
}

// ————————————————————————— Dashboard —————————————————————————

type Dashboard = {
  period: { year: number; month: number }
  suivi: { expected: number; submitted: number; late: number; submitted_pct: number }
  etat: { prepared: number; submitted: number; paid: number; late: number }
  flags: { high: number; medium: number; low: number; total: number }
  flags_by_activity: { activite: string; count: number }[]
}

function Dashboard({ adminKey, navigate }: { adminKey: string; navigate: (p: string) => void }) {
  const [data, setData] = useState<Dashboard | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    setError(null)
    void adminFetch<Dashboard>('/admin/dashboard', adminKey)
      .then(setData)
      .catch((e) => setError(String(e)))
  }, [adminKey])

  useEffect(load, [load])

  async function runDetection() {
    setBusy(true)
    try {
      await adminFetch('/admin/run-detection', adminKey, { method: 'POST' })
      load()
    } catch (e) {
      setError(String(e))
    } finally {
      setBusy(false)
    }
  }

  if (error) return <p className="ad-error">{error}</p>
  if (!data) return <p className="ad-muted">Chargement…</p>

  const maxActivity = Math.max(1, ...data.flags_by_activity.map((a) => a.count))

  return (
    <>
      <div className="ad-cards">
        <div className="ad-card">
          <span className="ad-card-label">Suivi du mois</span>
          <strong>
            {data.suivi.submitted} / {data.suivi.expected}
          </strong>
          <span className="ad-card-sub">
            {data.suivi.submitted_pct}% déposées · {data.suivi.late} en retard
          </span>
        </div>
        <div className="ad-card">
          <span className="ad-card-label">État des déclarations</span>
          <div className="ad-mini">
            <span>Préparées <b>{data.etat.prepared}</b></span>
            <span>Déposées <b>{data.etat.submitted}</b></span>
            <span>Payées <b>{data.etat.paid}</b></span>
            <span>En retard <b>{data.etat.late}</b></span>
          </div>
        </div>
        <div className="ad-card">
          <span className="ad-card-label">Risques ouverts</span>
          <div className="ad-risk-row">
            <button className="ad-risk" onClick={() => navigate('/admin/flags?severity=high')}>
              <i style={{ background: SEV_COLOR.high }} /> {data.flags.high} élevés
            </button>
            <button className="ad-risk" onClick={() => navigate('/admin/flags?severity=medium')}>
              <i style={{ background: SEV_COLOR.medium }} /> {data.flags.medium} moyens
            </button>
            <button className="ad-risk" onClick={() => navigate('/admin/flags?severity=low')}>
              <i style={{ background: SEV_COLOR.low }} /> {data.flags.low} faibles
            </button>
          </div>
        </div>
      </div>

      <div className="ad-panel">
        <div className="ad-panel-head">
          <h2>Drapeaux par activité</h2>
          <button className="ad-btn" onClick={() => void runDetection()} disabled={busy}>
            {busy ? 'Détection…' : 'Relancer la détection'}
          </button>
        </div>
        {data.flags_by_activity.length === 0 && <p className="ad-muted">Aucun drapeau.</p>}
        {data.flags_by_activity.map((a) => (
          <div className="ad-barchart" key={a.activite}>
            <span className="ad-barchart-label">{a.activite}</span>
            <span className="ad-barchart-track">
              <span
                className="ad-barchart-fill"
                style={{ width: `${(a.count / maxActivity) * 100}%` }}
              />
            </span>
            <b>{a.count}</b>
          </div>
        ))}
      </div>
    </>
  )
}

// ————————————————————————— Businesses —————————————————————————

type BusinessRow = {
  id: number
  matricule_fiscal: string
  name: string
  activite: string
  regime: string
  latest_status: string | null
  latest_period: string | null
  open_flags: number
  max_severity: Severity | null
}

const ETAT_LABEL: Record<string, string> = {
  prepared: 'Préparée',
  submitted: 'Déposée',
  paid: 'Payée',
}

function Businesses({ adminKey, navigate }: { adminKey: string; navigate: (p: string) => void }) {
  const [items, setItems] = useState<BusinessRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [flagsOnly, setFlagsOnly] = useState(false)

  useEffect(() => {
    const params = new URLSearchParams()
    if (q) params.set('activite', q)
    if (flagsOnly) params.set('has_open_flags', 'true')
    void adminFetch<{ items: BusinessRow[] }>(`/admin/businesses?${params}`, adminKey)
      .then((d) => setItems(d.items))
      .catch((e) => setError(String(e)))
  }, [adminKey, q, flagsOnly])

  return (
    <div className="ad-panel">
      <div className="ad-panel-head">
        <h2>Entreprises</h2>
        <div className="ad-filters">
          <input
            placeholder="Filtrer par activité…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <label className="ad-check">
            <input
              type="checkbox"
              checked={flagsOnly}
              onChange={(e) => setFlagsOnly(e.target.checked)}
            />
            Avec drapeaux
          </label>
        </div>
      </div>
      {error && <p className="ad-error">{error}</p>}
      <table className="ad-table">
        <thead>
          <tr>
            <th>Risque</th>
            <th>Nom</th>
            <th>Matricule</th>
            <th>Activité</th>
            <th>État</th>
            <th>Période</th>
            <th>Drapeaux</th>
          </tr>
        </thead>
        <tbody>
          {items.map((b) => (
            <tr key={b.id} onClick={() => navigate(`/admin/businesses/${b.id}`)} className="ad-row">
              <td>
                <SeverityDot severity={b.max_severity} />
              </td>
              <td>
                <strong>{b.name || '—'}</strong>
              </td>
              <td>{b.matricule_fiscal}</td>
              <td>{b.activite || '—'}</td>
              <td>{b.latest_status ? ETAT_LABEL[b.latest_status] ?? b.latest_status : '—'}</td>
              <td>{b.latest_period ?? '—'}</td>
              <td>{b.open_flags || ''}</td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={7} className="ad-muted">
                Aucune entreprise.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

// ————————————————————————— Business detail —————————————————————————

type Declaration = {
  id: number
  month: number
  year: number
  chiffre_affaires_declare: number
  tva_collectee: number
  tva_deductible: number
  retenue_totale: number
  status: string
}

type Flag = {
  id: number
  flag_type: string
  severity: Severity
  evidence: Record<string, unknown>
  explanation: string
  status: string
  resolution_note?: string | null
  period?: string | null
}

type FieldEdit = {
  id: number
  field_name: string
  ocr_extracted_value: string | null
  manual_value: string | null
  comment: string | null
  period: string
  edited_at: string
}

function BusinessDetail({
  adminKey,
  id,
  navigate,
  onReview,
}: {
  adminKey: string
  id: number
  navigate: (p: string) => void
  onReview: (flagId: number, status: 'escalated' | 'dismissed', note: string) => Promise<void>
}) {
  const [data, setData] = useState<{
    business: BusinessRow
    declarations: Declaration[]
    flags: Flag[]
    field_edits: FieldEdit[]
  } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    void adminFetch(`/admin/businesses/${id}`, adminKey)
      .then((d) => setData(d as never))
      .catch((e) => setError(String(e)))
  }, [adminKey, id])

  if (error) return <p className="ad-error">{error}</p>
  if (!data) return <p className="ad-muted">Chargement…</p>

  return (
    <>
      <button className="ad-back" onClick={() => navigate('/admin/businesses')}>
        ← Retour
      </button>
      <div className="ad-panel">
        <h2>{data.business.name}</h2>
        <p className="ad-muted">
          {data.business.matricule_fiscal} · {data.business.activite} ·{' '}
          {data.business.regime}
        </p>

        <h3>Historique des déclarations</h3>
        <table className="ad-table">
          <thead>
            <tr>
              <th>Période</th>
              <th>CA déclaré</th>
              <th>TVA collectée</th>
              <th>TVA déductible</th>
              <th>Retenue</th>
              <th>État</th>
            </tr>
          </thead>
          <tbody>
            {data.declarations.map((d) => (
              <tr key={d.id}>
                <td>
                  {String(d.month).padStart(2, '0')}/{d.year}
                </td>
                <td>{money(d.chiffre_affaires_declare)}</td>
                <td>{money(d.tva_collectee)}</td>
                <td>{money(d.tva_deductible)}</td>
                <td>{money(d.retenue_totale)}</td>
                <td>{ETAT_LABEL[d.status] ?? d.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <FlagList flags={data.flags} onReview={onReview} />

      <div className="ad-panel">
        <h3>Corrections OCR (field_edits)</h3>
        {data.field_edits.length === 0 && <p className="ad-muted">Aucune correction.</p>}
        <table className="ad-table">
          <thead>
            <tr>
              <th>Période</th>
              <th>Champ</th>
              <th>Valeur OCR</th>
              <th>Valeur manuelle</th>
              <th>Motif</th>
            </tr>
          </thead>
          <tbody>
            {data.field_edits.map((e) => (
              <tr key={e.id}>
                <td>{e.period}</td>
                <td>{e.field_name}</td>
                <td>{e.ocr_extracted_value ?? '—'}</td>
                <td>
                  <b>{e.manual_value ?? '—'}</b>
                </td>
                <td>{e.comment || <span className="ad-missing">motif manquant</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

// ————————————————————————— Flags —————————————————————————

function FlagList({
  flags,
  onReview,
}: {
  flags: Flag[]
  onReview: (flagId: number, status: 'escalated' | 'dismissed', note: string) => Promise<void>
}) {
  const [notes, setNotes] = useState<Record<number, string>>({})
  if (flags.length === 0) return <div className="ad-panel"><p className="ad-muted">Aucun drapeau.</p></div>
  return (
    <div className="ad-flags">
      {flags.map((f) => (
        <div className="ad-flag" key={f.id} style={{ borderLeftColor: SEV_COLOR[f.severity] }}>
          <div className="ad-flag-head">
            <SeverityBadge severity={f.severity} />
            <strong>{FLAG_LABEL[f.flag_type] ?? f.flag_type}</strong>
            {f.period && <span className="ad-muted">· {f.period}</span>}
            <span className={`ad-status ad-status-${f.status}`}>{f.status}</span>
          </div>
          <p className="ad-flag-expl">{f.explanation}</p>
          <details className="ad-evidence">
            <summary>Voir les chiffres exacts (preuves)</summary>
            <pre>{JSON.stringify(f.evidence, null, 2)}</pre>
          </details>
          {f.status === 'open' && (
            <div className="ad-flag-actions">
              <input
                placeholder="Note de résolution (obligatoire pour escalader)"
                value={notes[f.id] ?? ''}
                onChange={(e) => setNotes((n) => ({ ...n, [f.id]: e.target.value }))}
              />
              <button
                className="ad-btn ad-btn-danger"
                onClick={() => void onReview(f.id, 'escalated', notes[f.id] ?? '')}
              >
                Escalader
              </button>
              <button
                className="ad-btn"
                onClick={() => void onReview(f.id, 'dismissed', notes[f.id] ?? '')}
              >
                Rejeter
              </button>
            </div>
          )}
          {f.status !== 'open' && f.resolution_note ? (
            <p className="ad-muted">Résolution : {String(f.resolution_note)}</p>
          ) : null}
        </div>
      ))}
    </div>
  )
}

function GlobalFlags({
  adminKey,
  initialSeverity,
  navigate,
}: {
  adminKey: string
  initialSeverity: string | null
  navigate: (p: string) => void
}) {
  const [flags, setFlags] = useState<Flag[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    const params = new URLSearchParams({ status: 'open' })
    if (initialSeverity) params.set('severity', initialSeverity)
    void adminFetch<{ flags: Flag[] }>(`/admin/flags?${params}`, adminKey)
      .then((d) => setFlags(d.flags))
      .catch((e) => setError(String(e)))
  }, [adminKey, initialSeverity])

  useEffect(load, [load])

  async function review(flagId: number, status: 'escalated' | 'dismissed', note: string) {
    try {
      await adminFetch(`/admin/flags/${flagId}/review`, adminKey, {
        method: 'POST',
        body: JSON.stringify({ status, note }),
      })
      load()
    } catch (e) {
      setError(String(e))
    }
  }

  return (
    <>
      <div className="ad-panel-head">
        <h2>File des drapeaux {initialSeverity ? `· ${SEV_LABEL[initialSeverity as Severity]}` : ''}</h2>
        <button className="ad-btn" onClick={() => navigate('/admin/dashboard')}>
          Tableau de bord
        </button>
      </div>
      {error && <p className="ad-error">{error}</p>}
      <FlagList flags={flags} onReview={review} />
    </>
  )
}

// ————————————————————————— Shell —————————————————————————

export default function AdminApp() {
  const [adminKey, setAdminKey] = useState<string | null>(() =>
    localStorage.getItem(KEY_STORAGE),
  )
  const [path, setPath] = useState(() => window.location.pathname + window.location.search)

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname + window.location.search)
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const navigate = useCallback((p: string) => {
    window.history.pushState({}, '', p)
    setPath(p)
    window.scrollTo(0, 0)
  }, [])

  const review = useCallback(
    async (flagId: number, status: 'escalated' | 'dismissed', note: string) => {
      if (!adminKey) return
      await adminFetch(`/admin/flags/${flagId}/review`, adminKey, {
        method: 'POST',
        body: JSON.stringify({ status, note }),
      })
    },
    [adminKey],
  )

  if (!adminKey) return <AdminLogin onOk={setAdminKey} />

  const url = new URL(path, window.location.origin)
  const route = url.pathname
  const severity = url.searchParams.get('severity')

  let view: ReactElement
  const bizMatch = route.match(/^\/admin\/businesses\/(\d+)$/)
  if (bizMatch) {
    view = (
      <BusinessDetail
        adminKey={adminKey}
        id={Number(bizMatch[1])}
        navigate={navigate}
        onReview={review}
      />
    )
  } else if (route.startsWith('/admin/businesses')) {
    view = <Businesses adminKey={adminKey} navigate={navigate} />
  } else if (route.startsWith('/admin/flags')) {
    view = <GlobalFlags adminKey={adminKey} initialSeverity={severity} navigate={navigate} />
  } else {
    view = <Dashboard adminKey={adminKey} navigate={navigate} />
  }

  return (
    <div className="ad-app">
      <header className="ad-topbar">
        <div className="ad-brand">
          <span className="ad-flag">🇹🇳</span>
          <div>
            <strong>Administration DGI</strong>
            <span>Suivi &amp; détection — Réservé aux agents</span>
          </div>
        </div>
        <nav className="ad-nav">
          <button onClick={() => navigate('/admin/dashboard')}>Tableau de bord</button>
          <button onClick={() => navigate('/admin/businesses')}>Entreprises</button>
          <button onClick={() => navigate('/admin/flags')}>Drapeaux</button>
          <button
            className="ad-logout"
            onClick={() => {
              localStorage.removeItem(KEY_STORAGE)
              setAdminKey(null)
            }}
          >
            Quitter
          </button>
        </nav>
      </header>
      <main className="ad-main">{view}</main>
    </div>
  )
}
