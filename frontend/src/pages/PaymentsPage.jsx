import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RotateCcw } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

export function PaymentsPage({ roles = [] }) {
  const canReverse = roles.includes('administrator')
  const [selectedId, setSelectedId] = useState('')
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const client = useQueryClient()
  const payments = useQuery({ queryKey: ['payments'], queryFn: () => apiRequest('/payments?limit=100') })
  const reverse = useMutation({
    mutationFn: () => apiRequest('/payments/' + selectedId + '/reverse', { method: 'POST', body: { reason } }),
    onSuccess: () => { setReason(''); setError(''); setSelectedId(''); client.invalidateQueries({ queryKey: ['payments'] }); client.invalidateQueries({ queryKey: ['bills'] }) },
    onError: err => setError(err.message),
  })
  const rows = payments.data || []
  const selected = rows.find(row => row.id === selectedId)
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">FINANCIAL MANAGEMENT</div><h1>Payments</h1><p className="page-description">Review posted payment records. Reversals are administrator-only, reasoned, and audited; posted payments are never silently deleted.</p></div><span className="phase-tag">Audit protected</span></div>
    {payments.isPending ? <div className="empty-state">Loading payments…</div> : payments.isError ? <div className="error-panel"><strong>Payment history unavailable</strong><p>{payments.error.message}</p></div> : rows.length === 0 ? <div className="empty-state">No payment records found.</div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Payment</th><th>Bill</th><th>Amount</th><th>Method</th><th>Status</th><th>Receipt</th><th>Received</th><th>Action</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><strong>{row.id}</strong></td><td>{row.bill_id}</td><td>₱{Number(row.amount).toFixed(2)}</td><td>{row.payment_method}</td><td>{row.status}</td><td>{row.receipt_number || '—'}</td><td>{row.received_at ? new Date(row.received_at).toLocaleString() : '—'}</td><td>{canReverse && row.status === 'posted' && <button className="table-action" onClick={() => { setSelectedId(row.id); setReason(''); setError('') }}><RotateCcw size={13}/> Reverse</button>}</td></tr>)}</tbody></table></div>}
    {selected && canReverse && <section className="data-form receive-panel"><h2>Reverse payment</h2><p>Payment {selected.id} · ₱{Number(selected.amount).toFixed(2)}</p><form onSubmit={event => { event.preventDefault(); setError(''); reverse.mutate() }}><label>Reason for reversal<textarea required minLength="5" maxLength="2000" rows="3" value={reason} onChange={event => setReason(event.target.value)} placeholder="Explain why this posted payment must be reversed"/></label>{error && <p className="form-error" role="alert">{error}</p>}<div className="row-actions"><button className="primary-button" type="submit" disabled={reverse.isPending}>{reverse.isPending ? 'Reversing…' : 'Confirm reversal'}</button><button className="secondary-button" type="button" onClick={() => setSelectedId('')}>Cancel</button></div></form></section>}
    <div className="disclaimer">Reversals update bill balances and write an audit record. Verify the receipt and obtain the required authorization before reversing a payment.</div>
  </section>
}
