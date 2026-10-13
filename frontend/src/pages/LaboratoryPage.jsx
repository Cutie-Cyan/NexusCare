import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, FlaskConical } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

export function LaboratoryPage({ roles = [] }) {
  const canOrder = roles.includes('doctor')
  const canProcess = roles.includes('laboratory_staff')
  const canAuthorize = roles.some(role => ['administrator', 'cashier'].includes(role))
  const canReadResult = roles.some(role => ['administrator', 'doctor', 'nurse', 'laboratory_staff'].includes(role))
  const [form, setForm] = useState({ encounter_id: '', test_id: '', priority: 'routine', notes: '' })
  const [selectedOrderId, setSelectedOrderId] = useState('')
  const [resultText, setResultText] = useState('')
  const [authorizationReason, setAuthorizationReason] = useState('')
  const [error, setError] = useState('')
  const client = useQueryClient()
  const orders = useQuery({ queryKey: ['laboratory-orders'], queryFn: () => apiRequest('/laboratory-orders?limit=100') })
  const tests = useQuery({ queryKey: ['laboratory-tests'], queryFn: () => apiRequest('/laboratory-tests') })
  const encounters = useQuery({ queryKey: ['encounters', 'laboratory-options'], queryFn: () => apiRequest('/encounters?limit=100'), enabled: canOrder })
  const result = useQuery({
    queryKey: ['laboratory-result', selectedOrderId],
    queryFn: () => apiRequest('/laboratory-orders/' + selectedOrderId + '/result'),
    enabled: Boolean(selectedOrderId) && canReadResult,
    retry: false,
  })
  const createOrder = useMutation({
    mutationFn: () => apiRequest('/laboratory-orders', { method: 'POST', body: {
      encounter_id: form.encounter_id, test_id: form.test_id, priority: form.priority, notes: form.notes || null,
    } }),
    onSuccess: () => { setForm({ encounter_id: '', test_id: '', priority: 'routine', notes: '' }); setError(''); client.invalidateQueries({ queryKey: ['laboratory-orders'] }); client.invalidateQueries({ queryKey: ['bills'] }) },
    onError: err => setError(err.message),
  })
  const updateStatus = useMutation({
    mutationFn: ({ orderId, status }) => apiRequest('/laboratory-orders/' + orderId + '/status', { method: 'PATCH', body: { status } }),
    onSuccess: () => { setError(''); client.invalidateQueries({ queryKey: ['laboratory-orders'] }) },
    onError: err => setError(err.message),
  })
  const enterResult = useMutation({
    mutationFn: () => apiRequest('/laboratory-orders/' + selectedOrderId + '/result', { method: 'POST', body: { result_text: resultText } }),
    onSuccess: () => { setResultText(''); setError(''); client.invalidateQueries({ queryKey: ['laboratory-result', selectedOrderId] }) },
    onError: err => setError(err.message),
  })
  const verifyResult = useMutation({
    mutationFn: () => apiRequest('/laboratory-orders/' + selectedOrderId + '/verify-result', { method: 'POST' }),
    onSuccess: () => { setError(''); client.invalidateQueries({ queryKey: ['laboratory-result', selectedOrderId] }); client.invalidateQueries({ queryKey: ['laboratory-orders'] }) },
    onError: err => setError(err.message),
  })
  const authorizeBilling = useMutation({
    mutationFn: () => apiRequest('/laboratory-orders/' + selectedOrderId + '/billing-authorization', { method: 'POST', body: { reason: authorizationReason } }),
    onSuccess: () => { setAuthorizationReason(''); setError(''); client.invalidateQueries({ queryKey: ['laboratory-orders'] }) },
    onError: err => setError(err.message),
  })
  const orderRows = orders.data || []
  const testRows = tests.data || []
  const encounterRows = encounters.data || []
  const selectedOrder = orderRows.find(row => row.id === selectedOrderId)

  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">CLINICAL SERVICES</div><h1>Laboratory</h1><p className="page-description">Order tests, verify billing eligibility, process samples, enter results, and require a second staff member to release results.</p></div><span className="phase-tag">Payment gated</span></div>
    {canOrder && <form className="data-form" onSubmit={event => { event.preventDefault(); setError(''); createOrder.mutate() }}><h2><FlaskConical size={16}/> Order laboratory test</h2><div className="form-grid">
      <label>Open encounter<select required value={form.encounter_id} onChange={event => setForm({ ...form, encounter_id: event.target.value })}><option value="">Choose encounter</option>{encounterRows.filter(row => row.status === 'open').map(row => <option key={row.id} value={row.id}>{row.id} · {row.encounter_type} · {row.patient_id}</option>)}</select></label>
      <label>Test<select required value={form.test_id} onChange={event => setForm({ ...form, test_id: event.target.value })}><option value="">Choose test</option>{testRows.filter(row => row.is_active).map(row => <option key={row.id} value={row.id}>{row.name} · ₱{Number(row.base_fee).toFixed(2)}</option>)}</select></label>
      <label>Priority<select value={form.priority} onChange={event => setForm({ ...form, priority: event.target.value })}><option value="routine">Routine</option><option value="urgent">Urgent</option><option value="stat">STAT</option></select></label>
      <label>Notes<input value={form.notes} onChange={event => setForm({ ...form, notes: event.target.value })}/></label>
    </div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={createOrder.isPending || !encounterRows.length || !testRows.length}>{createOrder.isPending ? 'Ordering…' : 'Order test & add charge'}</button></form>}
    {orders.isPending ? <div className="empty-state">Loading laboratory orders…</div> : orders.isError ? <div className="error-panel"><strong>Laboratory orders unavailable</strong><p>{orders.error.message}</p></div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Order</th><th>Encounter</th><th>Test</th><th>Priority</th><th>Status</th><th>Actions</th></tr></thead><tbody>{orderRows.map(row => <tr key={row.id}><td><strong>{row.id}</strong></td><td>{row.encounter_id}</td><td>{testRows.find(test => test.id === row.test_id)?.name || row.test_id}</td><td>{row.priority}</td><td>{row.status}</td><td><div className="row-actions"><button className="table-action" onClick={() => { setSelectedOrderId(row.id); setError('') }}>Details / Result</button>{canProcess && row.status === 'ordered' && <button className="table-action" onClick={() => { setSelectedOrderId(row.id); updateStatus.mutate({ orderId: row.id, status: 'collected' }) }}>Collected</button>}{canProcess && ['ordered', 'collected'].includes(row.status) && <button className="table-action" onClick={() => { setSelectedOrderId(row.id); updateStatus.mutate({ orderId: row.id, status: 'in_progress' }) }}>Start</button>}</div></td></tr>)}</tbody></table></div>}
    {selectedOrderId && <section className="data-form receive-panel"><div className="section-heading"><h2>Order details</h2><button className="secondary-button" onClick={() => setSelectedOrderId('')}>Close</button></div><p><strong>Order:</strong> {selectedOrderId} · <strong>Status:</strong> {selectedOrder?.status || 'Loading'}</p>
      {!canReadResult ? <p className="history-empty">Your role can authorize billing arrangements but cannot view clinical result contents.</p> : result.isPending ? <p>Loading result…</p> : result.isError ? <p className="history-empty">No result is available yet.</p> : <div className="result-summary"><strong>Result status: {result.data.status}</strong><p>{result.data.result_text || JSON.stringify(result.data.result_data || {})}</p><span>Entered by {result.data.entered_by} · Verified by {result.data.verified_by || 'Not verified'}</span></div>}
      {canProcess && selectedOrder && ['collected', 'in_progress'].includes(selectedOrder.status) && <form onSubmit={event => { event.preventDefault(); setError(''); enterResult.mutate() }}><label>Result text<textarea required minLength="1" maxLength="10000" rows="4" value={resultText} onChange={event => setResultText(event.target.value)} placeholder="Enter result findings"/></label><button className="primary-button" type="submit" disabled={enterResult.isPending}>{enterResult.isPending ? 'Saving…' : 'Save result draft'}</button></form>}
      {canProcess && !result.isError && result.data?.status === 'draft' && <button className="primary-button" onClick={() => verifyResult.mutate()} disabled={verifyResult.isPending}><CheckCircle2 size={15}/>{verifyResult.isPending ? 'Verifying…' : 'Verify & release result'}</button>}
      {canAuthorize && selectedOrder && !['completed', 'cancelled'].includes(selectedOrder.status) && <form onSubmit={event => { event.preventDefault(); setError(''); authorizeBilling.mutate() }}><label>Authorized billing arrangement reason<textarea required minLength="3" maxLength="2000" rows="2" value={authorizationReason} onChange={event => setAuthorizationReason(event.target.value)} placeholder="Document the approved exception"/></label><button className="secondary-button" type="submit" disabled={authorizeBilling.isPending}>{authorizeBilling.isPending ? 'Authorizing…' : 'Authorize billing arrangement'}</button></form>}
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>}
    <div className="disclaimer">A paid charge or administrator/cashier authorization is required before the lab can collect/start a billable test. Result verification must be completed by a different laboratory staff account.</div>
  </section>
}
