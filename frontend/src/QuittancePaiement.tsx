export type QuittanceAmounts = {
  ca_ht: number
  tva_nette: number
  retenues_total: number
  tfp_amount: number
  foprolos_amount: number
  stamp_duty_total: number
  etablissement_tax_amount: number
  hotel_tax_amount: number
}

export type QuittanceData = {
  profileName: string
  taxId: string
  month: number
  year: number
  amounts: QuittanceAmounts
  paymentMode: string
  reference: string
  commande: string
  autorisation: string
  dateLabel: string
  pendingDgi?: boolean
}

function fmt(n: number): string {
  return n.toLocaleString('fr-TN', {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  })
}

function monthLabel(month: number, year: number): string {
  const name = new Date(year, month - 1, 1).toLocaleDateString('fr-FR', {
    month: 'long',
    year: 'numeric',
  })
  return name.charAt(0).toUpperCase() + name.slice(1)
}

export function buildQuittanceData(input: {
  profileName: string
  taxId: string
  month: number
  year: number
  amounts: QuittanceAmounts
  paymentMode: string
  now?: Date
  pendingDgi?: boolean
}): QuittanceData {
  const now = input.now ?? new Date()
  const mm = String(input.month).padStart(2, '0')
  const stamp = now
    .toISOString()
    .replace(/[-:TZ.]/g, '')
    .slice(0, 14)
  const tax = (input.taxId || 'X').replace(/\s+/g, '')
  return {
    profileName: input.profileName,
    taxId: input.taxId,
    month: input.month,
    year: input.year,
    amounts: input.amounts,
    paymentMode: input.paymentMode,
    reference: `DM-${input.year}${mm}-${tax}`,
    commande: `CMD-${stamp.slice(-10)}`,
    autorisation: `AUTH-${tax.slice(0, 6).toUpperCase()}-${stamp.slice(0, 8)}`,
    dateLabel: now.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    }),
    pendingDgi: input.pendingDgi ?? true,
  }
}

type Props = {
  data: QuittanceData
  onBack?: () => void
}

export default function QuittancePaiement({ data, onBack }: Props) {
  const a = data.amounts
  const tva = Math.max(0, a.tva_nette)
  const droits =
    Math.max(0, a.retenues_total) +
    Math.max(0, a.tfp_amount) +
    Math.max(0, a.foprolos_amount) +
    Math.max(0, a.stamp_duty_total) +
    Math.max(0, a.etablissement_tax_amount) +
    Math.max(0, a.hotel_tax_amount)
  const ttc = tva + droits
  const objet = `Déclaration mensuelle — ${monthLabel(data.month, data.year)}`

  function printPage() {
    window.print()
  }

  return (
    <section className="panel quittance-panel" data-spotlight="quittance">
      <div className="quittance" id="quittance-print">
        <header className="quittance-head">
          <p className="quittance-congrats">
            {data.pendingDgi ? 'Quittance créée' : 'Félicitations !'}
          </p>
          <h2 className="quittance-title">Quittance de Paiement</h2>
          <p className="quittance-ar" lang="ar" dir="rtl">
            وصل خلاص
          </p>
          {data.pendingDgi && (
            <p className="quittance-pending">En attente d&apos;approbation par la DGI</p>
          )}
        </header>

        <table className="quittance-info">
          <tbody>
            <tr>
              <td>
                <span className="q-label">Objet :</span>
                <span className="q-value">{objet}</span>
              </td>
              <td>
                <span className="q-label">Référence :</span>
                <span className="q-value">{data.reference}</span>
              </td>
            </tr>
            <tr>
              <td>
                <span className="q-label">Commande N° :</span>
                <span className="q-value">{data.commande}</span>
              </td>
              <td>
                <span className="q-label">Au profit de</span>
                <span className="q-value">Trésor Public — Receveur des Finances</span>
              </td>
            </tr>
            <tr>
              <td>
                <span className="q-label">Payée par :</span>
                <span className="q-value">
                  {data.profileName}
                  {data.taxId ? ` (${data.taxId})` : ''}
                </span>
              </td>
              <td>
                <span className="q-label">Date :</span>
                <span className="q-value">{data.dateLabel}</span>
              </td>
            </tr>
            <tr>
              <td>
                <span className="q-label">Montant en Dinars :</span>
                <span className="q-value q-amount">{fmt(ttc)} TND</span>
              </td>
              <td>
                <span className="q-label">Mode de Paiement :</span>
                <span className="q-value">{data.paymentMode}</span>
              </td>
            </tr>
            <tr>
              <td colSpan={2} className="q-auth">
                <span className="q-label">Autorisation :</span>
                <span className="q-value">{data.autorisation}</span>
              </td>
            </tr>
          </tbody>
        </table>

        <div className="quittance-print-row">
          <button type="button" className="quittance-print-link" onClick={printPage}>
            Imprimer cette page
          </button>
        </div>

        <table className="quittance-totals">
          <thead>
            <tr>
              <th>Montant HT</th>
              <th>TVA</th>
              <th>DROIT DE L&apos;ETAT</th>
              <th>TTC</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{fmt(a.ca_ht)}</td>
              <td>{fmt(tva)}</td>
              <td>{fmt(droits)}</td>
              <td className="q-ttc">{fmt(ttc)}</td>
            </tr>
          </tbody>
        </table>
      </div>

      {onBack && (
        <div className="actions quittance-actions no-print">
          <button type="button" className="btn btn-ghost" onClick={onBack}>
            Retour au formulaire
          </button>
          <button type="button" className="btn btn-primary" onClick={printPage}>
            Imprimer la quittance
          </button>
        </div>
      )}
    </section>
  )
}
