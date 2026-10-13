import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { PackageCheck, Pill } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const emptyBatch = { medicine_id: '', batch_number: '', quantity: '1', unit_cost: '0.00', selling_price: '0.00', expires_on: '' }

export function PharmacyPage() {
  const [batchForm, setBatchForm] = useState(emptyBatch)
  const [selectedPrescriptionId, setSelectedPrescriptionId] = useState('')
  const [dispenseForm, setDispenseForm] = useState({ item_id: '', medicine_batch_id: '', quantity: '1' })
  const [error, setError] = useState('')
  const client = useQueryClient()
  const stock = useQuery({ queryKey: ['pharmacy-stock'], queryFn: () => apiRequest('/pharmacy/stock') })
  const medicines = useQuery({ queryKey: ['medicines'], queryFn: () => apiRequest('/medicines') })
  const batches = useQuery({ queryKey: ['medicine-batches'], queryFn: () => apiRequest('/medicine-batches') })
  const prescriptions = useQuery({ queryKey: ['prescriptions'], queryFn: () => apiRequest('/prescriptions?limit=100') })
  const prescriptionItems = useQuery({
    queryKey: ['prescription-items', selectedPrescriptionId],
    queryFn: () => apiRequest('/prescriptions/' + selectedPrescriptionId + '/items'),
    enabled: Boolean(selectedPrescriptionId),
  })
  const createBatch = useMutation({
    mutationFn: () => apiRequest('/medicine-batches', { method: 'POST', body: {
      medicine_id: batchForm.medicine_id, batch_number: batchForm.batch_number,
      quantity: Number(batchForm.quantity), unit_cost: batchForm.unit_cost,
      selling_price: batchForm.selling_price, expires_on: batchForm.expires_on || null,
    } }),
    onSuccess: () => { setBatchForm(emptyBatch); setError(''); client.invalidateQueries({ queryKey: ['medicine-batches'] }); client.invalidateQueries({ queryKey: ['pharmacy-stock'] }) },
    onError: err => setError(err.message),
  })
  const dispense = useMutation({
    mutationFn: () => apiRequest('/prescription-items/' + dispenseForm.item_id + '/dispense', { method: 'POST', body: {
      medicine_batch_id: dispenseForm.medicine_batch_id, quantity: Number(dispenseForm.quantity),
    } }),
    onSuccess: () => {
      setError('')
      client.invalidateQueries({ queryKey: ['pharmacy-stock'] })
      client.invalidateQueries({ queryKey: ['medicine-batches'] })
      client.invalidateQueries({ queryKey: ['prescription-items', selectedPrescriptionId] })
      client.invalidateQueries({ queryKey: ['prescriptions'] })
      client.invalidateQueries({ queryKey: ['bills'] })
    },
    onError: err => setError(err.message),
  })
  const medicineRows = medicines.data || []
  const batchRows = batches.data || []
  const prescriptionRows = prescriptions.data || []
  const itemRows = prescriptionItems.data || []
  const selectedItem = itemRows.find(item => item.id === dispenseForm.item_id)
  const matchingBatches = batchRows.filter(batch => selectedItem && batch.medicine_id === selectedItem.medicine_id && batch.quantity_on_hand > 0)

  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">HOSPITAL OPERATIONS</div><h1>Pharmacy</h1><p className="page-description">Manage medicine batches and dispense only against valid prescription items. Successful dispensing updates stock and adds a bill charge.</p></div><span className="phase-tag">Inventory controlled</span></div>
    <form className="data-form" onSubmit={event => { event.preventDefault(); setError(''); createBatch.mutate() }}>
      <h2><PackageCheck size={16}/> Receive medicine batch</h2><div className="form-grid">
        <label>Medicine<select required value={batchForm.medicine_id} onChange={event => setBatchForm({ ...batchForm, medicine_id: event.target.value })}><option value="">Choose medicine</option>{medicineRows.map(row => <option key={row.id} value={row.id}>{row.name} {row.strength || ''} · {row.code}</option>)}</select></label>
        <label>Batch number<input required value={batchForm.batch_number} onChange={event => setBatchForm({ ...batchForm, batch_number: event.target.value })}/></label>
        <label>Quantity<input required type="number" min="1" step="1" value={batchForm.quantity} onChange={event => setBatchForm({ ...batchForm, quantity: event.target.value })}/></label>
        <label>Unit cost (PHP)<input required type="number" min="0" step="0.01" value={batchForm.unit_cost} onChange={event => setBatchForm({ ...batchForm, unit_cost: event.target.value })}/></label>
        <label>Selling price (PHP)<input required type="number" min="0" step="0.01" value={batchForm.selling_price} onChange={event => setBatchForm({ ...batchForm, selling_price: event.target.value })}/></label>
        <label>Expiry date<input type="date" value={batchForm.expires_on} onChange={event => setBatchForm({ ...batchForm, expires_on: event.target.value })}/></label>
      </div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={createBatch.isPending || !medicineRows.length}>{createBatch.isPending ? 'Receiving…' : 'Add batch to stock'}</button>
    </form>
    <section className="data-form"><h2><Pill size={16}/> Dispense prescription</h2><div className="form-grid">
      <label>Prescription<select required value={selectedPrescriptionId} onChange={event => { setSelectedPrescriptionId(event.target.value); setDispenseForm({ item_id: '', medicine_batch_id: '', quantity: '1' }) }}><option value="">Choose prescription</option>{prescriptionRows.filter(row => row.status !== 'cancelled').map(row => <option key={row.id} value={row.id}>{row.id} · {row.status}</option>)}</select></label>
      <label>Prescription item<select required value={dispenseForm.item_id} onChange={event => setDispenseForm({ ...dispenseForm, item_id: event.target.value, medicine_batch_id: '' })}><option value="">Choose item</option>{itemRows.map(item => <option key={item.id} value={item.id}>{medicineRows.find(medicine => medicine.id === item.medicine_id)?.name || item.medicine_id} · qty {item.quantity}</option>)}</select></label>
      <label>Matching batch<select required value={dispenseForm.medicine_batch_id} onChange={event => setDispenseForm({ ...dispenseForm, medicine_batch_id: event.target.value })}><option value="">Choose batch</option>{matchingBatches.map(batch => <option key={batch.id} value={batch.id}>{batch.batch_number} · stock {batch.quantity_on_hand} · expires {batch.expires_on || 'not set'}</option>)}</select></label>
      <label>Quantity to dispense<input required type="number" min="1" step="1" value={dispenseForm.quantity} onChange={event => setDispenseForm({ ...dispenseForm, quantity: event.target.value })}/></label>
    </div><button className="primary-button" type="button" onClick={() => { setError(''); dispense.mutate() }} disabled={dispense.isPending || !dispenseForm.item_id || !dispenseForm.medicine_batch_id}>{dispense.isPending ? 'Dispensing…' : 'Dispense & bill'}</button></section>
    {stock.isPending ? <div className="empty-state">Loading pharmacy stock…</div> : stock.isError ? <div className="error-panel"><strong>Stock unavailable</strong><p>{stock.error.message}</p></div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Medicine</th><th>Total stock</th><th>Reorder level</th><th>Status</th><th>Batch count</th></tr></thead><tbody>{(stock.data || []).map(row => <tr key={row.medicine_id}><td><strong>{row.medicine_name}</strong></td><td>{row.total_quantity}</td><td>{row.reorder_level}</td><td>{row.stock_status}</td><td>{row.batches?.length || 0}</td></tr>)}</tbody></table></div>}
    <div className="disclaimer">The backend validates medicine match, batch expiry, available quantity, and prescribed remaining quantity. Never use real medication records in this demo environment.</div>
  </section>
}
