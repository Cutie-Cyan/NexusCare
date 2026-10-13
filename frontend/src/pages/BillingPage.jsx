import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ReceiptText, Wallet } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const emptyBill = { patient_id: '', service_id: '', bill_number: '', quantity: '1' }

export function BillingPage({ roles = [] }) {
  const canManage = roles.some(role => ['administrator', 'information_officer', 'cashier'].includes(role))
  const isPatient = roles.includes('patient') && !canManage
  const [billForm, setBillForm] = useState(emptyBill)
  const [selectedBillId, setSelectedBillId] = useState('')
  const [paymentForm, setPaymentForm] = useState({ amount: '', payment_method: 'cash' })
  const [error, setError] = useState('')
  const [receiptNumber, setReceiptNumber] = useState('')
  const client = useQueryClient()
  const bills = useQuery({ queryKey: ['bills'], queryFn: () => apiRequest('/bills?limit=100') })
  const patients = useQuery({ queryKey: ['patients', 'billing-options'], queryFn: () => apiRequest('/patients?limit=100'), enabled: canManage })
  const services = useQuery({ queryKey: ['service-catalog'], queryFn: () => apiRequest('/service-catalog'), enabled: canManage })
  const balance = useQuery({ queryKey: ['bill-balance', selectedBillId], queryFn: () => apiRequest('/bills/' + selectedBillId + '/balance'), enabled: Boolean(selectedBillId) })
  const createBill = useMutation({
    mutationFn: () => {
      const service = (services.data || []).find(row => row.id === billForm.service_id)
      if (!service) throw new Error('Choose a service from the catalog.')
      return apiRequest('/bills', { method: 'POST', body: {
        patient_id: billForm.patient_id, encounter_id: null, bill_number: billForm.bill_number,
        adjustments: '0.00',
        items: [{ description: service.name, quantity: Number(billForm.quantity), unit_price: service.price, service_id: service.id }],
      } })
    },
    onSuccess: () => { setBillForm(emptyBill); setError(''); client.invalidateQueries({ queryKey: ['bills'] }) },
    onError: err => setError(err.message),
  })
  const postPayment = useMutation({
    mutationFn: ({ billId, amount, payment_method, idempotencyKey }) => apiRequest('/bills/' + billId + '/payments', {
      method: 'POST', headers: { 'Idempotency-Key': idempotencyKey }, body: { amount, payment_method },
    }),
    onSuccess: data => {
      setReceiptNumber(data.receipt_number)
      setError('')
      setPaymentForm({ amount: '', payment_method: 'cash' })
      client.invalidateQueries({ queryKey: ['bills'] })
      client.invalidateQueries({ queryKey: ['payments'] })
      client.invalidateQueries({ queryKey: ['bill-balance', selectedBillId] })
    },
    onError: err => setError(err.message),
  })
  const patientRows = patients.data || []
  const patientById = Object.fromEntries(patientRows.map(row => [row.id, row]))
  const serviceRows = (services.data || []).filter(row => row.is_active !== false)
  const billRows = bills.data || []

  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">FINANCIAL MANAGEMENT</div><h1>Billing</h1><p className="page-description">{isPatient ? 'View your bills and payment balances.' : 'Create itemized bills, record payments, and retrieve receipts.'}</p></div><span className="phase-tag">PHP · Exact decimal amounts</span></div>
    {canManage && <form className="data-form" onSubmit={event => { event.preventDefault(); setError(''); setReceiptNumber(''); createBill.mutate() }}>
      <h2><Wallet size={16}/> Create bill</h2><div className="form-grid">
        <label>Patient<select required value={billForm.patient_id} onChange={event => setBillForm({ ...billForm, patient_id: event.target.value })}><option value="">Choose patient</option>{patientRows.map(row => <option key={row.id} value={row.id}>{row.last_name}, {row.first_name} · {row.medical_record_number}</option>)}</select></label>
        <label>Bill number<input required minLength="3" maxLength="50" value={billForm.bill_number} onChange={event => setBillForm({ ...billForm, bill_number: event.target.value.toUpperCase() }} placeholder="BILL-2026-001"/></label>
        <label>Service<select required value={billForm.service_id} onChange={event => setBillForm({ ...billForm, service_id: event.target.value })}><option value="">Choose service</option>{serviceRows.map(row => <option key={row.id} value={row.id}>{row.name} · ₱{Number(row.price).toFixed(2)}</option>)}</select></label>
        <label>Quantity<input required type="number" min="1" max="100000" step="1" value={billForm.quantity} onChange={event => setBillForm({ ...billForm, quantity: event.target.value })}/></label>
      </div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={createBill.isPending || !patientRows.length || !serviceRows.length}>{createBill.isPending ? 'Creating…' : 'Create bill'}</button>
    </form>}
    {receiptNumber && <div className="success-panel"><ReceiptText size={17}/><span>Payment posted. Receipt number: <strong>{receiptNumber}</strong></span></div>}
    {bills.isPending ? <div className="empty-state">Loading bills…</div> : bills.isError ? <div className="error-panel"><strong>Bills unavailable</strong><p>{bills.error.message}</p></div> : billRows.length === 0 ? <div className="empty-state">No bills found.</div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Bill number</th><th>Patient</th><th>Total</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead><tbody>{billRows.map(row => <tr key={row.id}><td><strong>{row.bill_number}</strong></td><td>{patientById[row.patient_id] ? patientById[row.patient_id].last_name + ', ' + patientById[row.patient_id].first_name : row.patient_id}</td><td>₱{Number(row.total).toFixed(2)}</td><td>{row.status}</td><td>{row.created_at ? new Date(row.created_at).toLocaleString() : '—'}</td><td><div className="row-actions"><button className="table-action" onClick={() => { setSelectedBillId(row.id); setReceiptNumber(''); setError('') }}>Balance / Pay</button></div></td></tr>)}</tbody></table></div>}
    {selectedBillId && <section className="data-form receive-panel"><div className="section-heading"><h2>Bill balance</h2><button className="secondary-button" onClick={() => setSelectedBillId('')}>Close</button></div>{balance.isPending ? <p>Loading balance…</p> : balance.isError ? <p className="form-error">{balance.error.message}</p> : <div className="metric-grid compact-metrics"><article className="metric-card"><span>Total</span><strong>₱{Number(balance.data.total).toFixed(2)}</strong></article><article className="metric-card"><span>Paid</span><strong>₱{Number(balance.data.paid).toFixed(2)}</strong></article><article className="metric-card"><span>Balance</span><strong>₱{Number(balance.data.balance).toFixed(2)}</strong></article></div>}
      {canManage && balance.data?.balance > 0 && <form onSubmit={event => { event.preventDefault(); setError(''); postPayment.mutate({ billId: selectedBillId, amount: paymentForm.amount, payment_method: paymentForm.payment_method, idempotencyKey: 'NC-' + crypto.randomUUID() }) }}><div className="form-grid"><label>Payment amount (PHP)<input required type="number" min="0.01" max={balance.data.balance} step="0.01" value={paymentForm.amount} onChange={event => setPaymentForm({ ...paymentForm, amount: event.target.value })}/></label><label>Payment method<select value={paymentForm.payment_method} onChange={event => setPaymentForm({ ...paymentForm, payment_method: event.target.value })}><option value="cash">Cash</option><option value="card">Card</option><option value="bank_transfer">Bank transfer</option><option value="ewallet">E-wallet</option><option value="insurance">Insurance</option><option value="other">Other</option></select></label></div><button className="primary-button" type="submit" disabled={postPayment.isPending}>{postPayment.isPending ? 'Posting…' : 'Post payment & issue receipt'}</button></form>}
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>}
    <div className="disclaimer">Payments require an idempotency key. Posted payments are not deleted; reversals are audited and restricted to administrators. Automatically generated laboratory, pharmacy, and professional fees are added by their respective workflows.</div>
  </section>
}
