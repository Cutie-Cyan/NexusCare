import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, PackageCheck, Plus } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const emptyForm = { request_number: '', supplier_id: '', inventory_item_id: '', requested_quantity: '1', unit_cost: '0.00', notes: '' }

export function ProcurementPage() {
  const [form, setForm] = useState(emptyForm)
  const [selectedRequestId, setSelectedRequestId] = useState('')
  const [receiveForm, setReceiveForm] = useState({ item_id: '', quantity_received: '1', supplier_reference: '', notes: '' })
  const [error, setError] = useState('')
  const client = useQueryClient()
  const requests = useQuery({ queryKey: ['procurement-requests'], queryFn: () => apiRequest('/procurement/requests?limit=100') })
  const suppliers = useQuery({ queryKey: ['suppliers'], queryFn: () => apiRequest('/suppliers') })
  const inventory = useQuery({ queryKey: ['inventory-items'], queryFn: () => apiRequest('/inventory/items') })
  const items = useQuery({
    queryKey: ['procurement-items', selectedRequestId],
    queryFn: () => apiRequest('/procurement/requests/' + selectedRequestId + '/items'),
    enabled: Boolean(selectedRequestId),
  })
  const create = useMutation({
    mutationFn: () => apiRequest('/procurement/requests', { method: 'POST', body: {
      request_number: form.request_number, supplier_id: form.supplier_id || null, notes: form.notes || null,
      items: [{ inventory_item_id: form.inventory_item_id, requested_quantity: form.requested_quantity, unit_cost: form.unit_cost, notes: form.notes || null }],
    } }),
    onSuccess: () => { setForm(emptyForm); setError(''); client.invalidateQueries({ queryKey: ['procurement-requests'] }) },
    onError: err => setError(err.message),
  })
  const approve = useMutation({
    mutationFn: id => apiRequest('/procurement/requests/' + id + '/approve', { method: 'POST' }),
    onSuccess: () => { setError(''); client.invalidateQueries({ queryKey: ['procurement-requests'] }) },
    onError: err => setError(err.message),
  })
  const receive = useMutation({
    mutationFn: () => apiRequest('/procurement/requests/' + selectedRequestId + '/items/' + receiveForm.item_id + '/receive', { method: 'POST', body: {
      quantity_received: receiveForm.quantity_received,
      supplier_reference: receiveForm.supplier_reference || null, notes: receiveForm.notes || null,
    } }),
    onSuccess: () => {
      setError('')
      client.invalidateQueries({ queryKey: ['procurement-requests'] })
      client.invalidateQueries({ queryKey: ['procurement-items', selectedRequestId] })
      client.invalidateQueries({ queryKey: ['inventory-items'] })
    },
    onError: err => setError(err.message),
  })
  const requestRows = requests.data || []
  const inventoryRows = inventory.data || []
  const supplierRows = suppliers.data || []
  const itemRows = items.data || []

  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">HOSPITAL OPERATIONS</div><h1>Procurement</h1><p className="page-description">Submit supply requests, approve them, and record deliveries. Receiving updates stock and the inventory ledger atomically.</p></div><span className="phase-tag">Admin / Pharmacy</span></div>
    <form className="data-form" onSubmit={event => { event.preventDefault(); setError(''); create.mutate() }}>
      <h2><Plus size={16}/> Submit replenishment request</h2><div className="form-grid">
        <label>Request number<input required minLength="3" maxLength="50" value={form.request_number} onChange={event => setForm({ ...form, request_number: event.target.value.toUpperCase() })} placeholder="PR-2026-001"/></label>
        <label>Supplier<select required value={form.supplier_id} onChange={event => setForm({ ...form, supplier_id: event.target.value })}><option value="">Choose supplier</option>{supplierRows.map(row => <option key={row.id} value={row.id}>{row.name} ({row.code})</option>)}</select></label>
        <label>Inventory item<select required value={form.inventory_item_id} onChange={event => setForm({ ...form, inventory_item_id: event.target.value })}><option value="">Choose item</option>{inventoryRows.map(row => <option key={row.id} value={row.id}>{row.name} · {row.code}</option>)}</select></label>
        <label>Quantity<input required type="number" min="0.001" step="0.001" value={form.requested_quantity} onChange={event => setForm({ ...form, requested_quantity: event.target.value })}/></label>
        <label>Unit cost (PHP)<input required type="number" min="0" step="0.01" value={form.unit_cost} onChange={event => setForm({ ...form, unit_cost: event.target.value })}/></label>
        <label>Notes<input value={form.notes} onChange={event => setForm({ ...form, notes: event.target.value })} placeholder="Optional delivery notes"/></label>
      </div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={create.isPending || !inventoryRows.length || !supplierRows.length}>{create.isPending ? 'Submitting…' : 'Submit request'}</button>
    </form>
    <div className="section-heading"><h2>Procurement requests</h2><span>{requestRows.length} REQUESTS</span></div>
    {requests.isPending ? <div className="empty-state">Loading procurement requests…</div> : requests.isError ? <div className="error-panel"><strong>Requests unavailable</strong><p>{requests.error.message}</p></div> : requestRows.length === 0 ? <div className="empty-state"><PackageCheck size={24}/><strong>No procurement requests yet</strong><span>Submit a request above to begin the approval and receiving workflow.</span></div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Request</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead><tbody>{requestRows.map(row => <tr key={row.id}><td><strong>{row.request_number}</strong></td><td>{row.status}</td><td>{row.created_at ? new Date(row.created_at).toLocaleString() : '—'}</td><td><div className="row-actions">{row.status === 'submitted' && <button className="table-action" onClick={() => approve.mutate(row.id)} disabled={approve.isPending}><CheckCircle2 size={13}/> Approve</button>}{['approved', 'partially_received'].includes(row.status) && <button className="table-action" onClick={() => { setSelectedRequestId(row.id); setReceiveForm({ item_id: '', quantity_received: '1', supplier_reference: '', notes: '' }) }}>Receive stock</button>}<button className="table-action" onClick={() => setSelectedRequestId(current => current === row.id ? '' : row.id)}>Items</button></div></td></tr>)}</tbody></table></div>}
    {selectedRequestId && <section className="data-form receive-panel"><h2><PackageCheck size={16}/> Request items</h2>{items.isPending ? <p>Loading request items…</p> : items.isError ? <p className="form-error">{items.error.message}</p> : <><div className="data-table-wrap"><table className="data-table"><thead><tr><th>Item ID</th><th>Requested</th><th>Received</th><th>Unit cost</th></tr></thead><tbody>{itemRows.map(item => <tr key={item.id}><td>{item.inventory_item_id}</td><td>{item.requested_quantity}</td><td>{item.received_quantity}</td><td>₱{Number(item.unit_cost).toFixed(2)}</td></tr>)}</tbody></table></div><form onSubmit={event => { event.preventDefault(); setError(''); receive.mutate() }}><div className="form-grid"><label>Item<select required value={receiveForm.item_id} onChange={event => setReceiveForm({ ...receiveForm, item_id: event.target.value })}><option value="">Choose item</option>{itemRows.filter(item => Number(item.received_quantity) < Number(item.requested_quantity)).map(item => <option key={item.id} value={item.id}>{item.inventory_item_id} · remaining {Number(item.requested_quantity) - Number(item.received_quantity)}</option>)}</select></label><label>Quantity received<input required type="number" min="0.001" step="0.001" value={receiveForm.quantity_received} onChange={event => setReceiveForm({ ...receiveForm, quantity_received: event.target.value })}/></label><label>Supplier delivery reference<input value={receiveForm.supplier_reference} onChange={event => setReceiveForm({ ...receiveForm, supplier_reference: event.target.value })}/></label><label>Notes<input value={receiveForm.notes} onChange={event => setReceiveForm({ ...receiveForm, notes: event.target.value })}/></label></div><div className="row-actions"><button className="primary-button" type="submit" disabled={receive.isPending || !receiveForm.item_id}>{receive.isPending ? 'Recording…' : 'Record delivery'}</button><button className="secondary-button" type="button" onClick={() => setSelectedRequestId('')}>Close</button></div></form></>}</section>}
    <div className="disclaimer">Only approved requests can be received. The backend rejects over-receipts and locks inventory rows to prevent stock from being added twice by concurrent deliveries.</div>
  </section>
}
