import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Printer, ReceiptText, Search } from 'lucide-react'
import { apiRequest, API_BASE_URL } from '../lib/api.js'
import { supabase } from '../lib/supabase.js'

const dateLabel = value => value ? new Date(value).toLocaleString() : '—'
const money = value => '₱' + Number(value || 0).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

async function downloadReceiptPdf(receiptNumber) {
  const { data, error } = await supabase.auth.getSession()
  if (error) throw new Error(error.message)
  if (!data.session?.access_token) throw new Error('Please sign in again.')
  const response = await fetch(API_BASE_URL + '/receipts/' + encodeURIComponent(receiptNumber) + '/pdf', {
    headers: { Authorization: 'Bearer ' + data.session.access_token },
  })
  if (!response.ok) throw new Error('Could not download the receipt PDF.')
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'receipt-' + receiptNumber + '.pdf'
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export function ReceiptsPage() {
  const [search, setSearch] = useState('')
  const [selectedNumber, setSelectedNumber] = useState('')
  const [downloadError, setDownloadError] = useState('')
  const [downloading, setDownloading] = useState(false)
  const receipts = useQuery({ queryKey: ['receipts'], queryFn: () => apiRequest('/receipts?limit=100') })
  const detail = useQuery({ queryKey: ['receipt-detail', selectedNumber], queryFn: () => apiRequest('/receipts/' + encodeURIComponent(selectedNumber)), enabled: Boolean(selectedNumber) })
  const rows = receipts.data || []
  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase()
    return term ? rows.filter(row => JSON.stringify(row).toLowerCase().includes(term)) : rows
  }, [rows, search])
  return <section className="page-wrap receipt-page">
    <div className="page-heading"><div><div className="eyebrow">FINANCIAL MANAGEMENT</div><h1>Receipts</h1><p className="page-description">Search issued receipts and open a printable copy. Access is limited to authorized billing staff or the linked patient.</p></div></div>
    <div className="table-toolbar"><div className="search-field"><Search size={16}/><input aria-label="Search receipts" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search receipt or bill number"/></div><span>{filtered.length} receipt{filtered.length === 1 ? '' : 's'}</span></div>
    {receipts.isPending ? <div className="empty-state">Loading receipts…</div>
      : receipts.isError ? <div className="error-panel"><strong>Receipts unavailable</strong><p>{receipts.error.message}</p></div>
      : filtered.length === 0 ? <div className="empty-state"><ReceiptText size={24}/><strong>No receipts found</strong><span>Receipts appear after a payment is successfully posted.</span></div>
      : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Receipt number</th><th>Bill</th><th>Amount</th><th>Method</th><th>Status</th><th>Issued</th><th>Action</th></tr></thead><tbody>{filtered.map(row => <tr key={row.receipt_number}><td><strong>{row.receipt_number}</strong></td><td>{row.bill_number}</td><td>{money(row.payment_amount)}</td><td>{row.payment_method}</td><td>{row.payment_status}</td><td>{dateLabel(row.issued_at)}</td><td><button className="table-action" onClick={() => setSelectedNumber(row.receipt_number)}>View / print</button></td></tr>)}</tbody></table></div>}
    {selectedNumber && <div className="modal-scrim" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) setSelectedNumber('') }}><section className="history-modal" role="dialog" aria-modal="true" aria-labelledby="receipt-title">
      <header><div><div className="eyebrow">NEXUSCARE · PAYMENT RECORD</div><h2 id="receipt-title">Receipt</h2><p>{selectedNumber}</p></div><div className="row-actions"><button className="secondary-button" onClick={() => window.print()}><Printer size={14}/> Print</button><button className="secondary-button" disabled={downloading} onClick={async () => { setDownloading(true); setDownloadError(''); try { await downloadReceiptPdf(selectedNumber) } catch (error) { setDownloadError(error.message) } finally { setDownloading(false) } }}>{downloading ? 'Downloading…' : 'Download PDF'}</button></div></header>
      {downloadError && <p className="form-error" role="alert">{downloadError}</p>}
      {detail.isPending ? <div className="empty-state">Loading receipt…</div>
        : detail.isError ? <div className="error-panel"><strong>Could not load receipt</strong><p>{detail.error.message}</p></div>
        : <div className="history-content"><article className="receipt-printable history-section">
          <div className="receipt-brand"><ReceiptText size={24}/><div><h2>NexusCare Hospital</h2><p>Official payment receipt · Keep this for your records</p></div></div>
          <div className="receipt-detail-grid"><span>Receipt number<strong>{detail.data.receipt_number}</strong></span><span>Issued at<strong>{dateLabel(detail.data.issued_at)}</strong></span><span>Bill number<strong>{detail.data.bill_number}</strong></span><span>Payment status<strong>{detail.data.payment_status}</strong></span><span>Payment method<strong>{detail.data.payment_method}</strong></span><span>Patient record ID<strong>{detail.data.patient_id}</strong></span></div>
          <div className="receipt-total"><span>Payment amount</span><strong>{money(detail.data.payment_amount)}</strong></div>
          <p className="disclaimer">This receipt confirms the recorded payment transaction. It does not represent a medical or insurance claim.</p>
        </article></div>}
    </section></div>}
  </section>
}
