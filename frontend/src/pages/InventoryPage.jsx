import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Package, Plus, RefreshCw } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const emptyItem = { code: '', name: '', category: 'medical_supply', unit: 'piece', reorder_level: '0', unit_cost: '0.00', supplier_id: '' }

export function InventoryPage() {
  const [itemForm, setItemForm] = useState(emptyItem)
  const [movement, setMovement] = useState({ item_id: '', transaction_type: 'receipt', quantity: '1', notes: '' })
  const [error, setError] = useState('')
  const client = useQueryClient()
  const items = useQuery({ queryKey: ['inventory-items'], queryFn: () => apiRequest('/inventory/items') })
  const suppliers = useQuery({ queryKey: ['suppliers'], queryFn: () => apiRequest('/suppliers') })
  const createItem = useMutation({
    mutationFn: () => apiRequest('/inventory/items', { method: 'POST', body: { ...itemForm, supplier_id: itemForm.supplier_id || null } }),
    onSuccess: () => { setItemForm(emptyItem); setError(''); client.invalidateQueries({ queryKey: ['inventory-items'] }) },
    onError: err => setError(err.message),
  })
  const recordMovement = useMutation({
    mutationFn: () => {
      const value = Number(movement.quantity)
      const quantity_delta = movement.transaction_type === 'issue' ? -Math.abs(value) : movement.transaction_type === 'receipt' ? Math.abs(value) : value
      return apiRequest('/inventory/items/' + movement.item_id + '/movements', { method: 'POST', body: {
        quantity_delta, transaction_type: movement.transaction_type, notes: movement.notes || null,
      } })
    },
    onSuccess: () => { setError(''); client.invalidateQueries({ queryKey: ['inventory-items'] }) },
    onError: err => setError(err.message),
  })
  const rows = items.data || []
  const supplierRows = suppliers.data || []
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">HOSPITAL OPERATIONS</div><h1>Inventory</h1><p className="page-description">Maintain supply catalog records and post auditable stock movements. The API rejects any movement that would make stock negative.</p></div><span className="phase-tag">Admin / Pharmacy</span></div>
    <form className="data-form" onSubmit={event => { event.preventDefault(); setError(''); createItem.mutate() }}><h2><Plus size={16}/> Add inventory item</h2><div className="form-grid">
      <label>Item code<input required minLength="2" maxLength="50" value={itemForm.code} onChange={event => setItemForm({ ...itemForm, code: event.target.value.toUpperCase() })}/></label>
      <label>Name<input required minLength="2" maxLength="180" value={itemForm.name} onChange={event => setItemForm({ ...itemForm, name: event.target.value })}/></label>
      <label>Category<input required value={itemForm.category} onChange={event => setItemForm({ ...itemForm, category: event.target.value })}/></label>
      <label>Unit<input required value={itemForm.unit} onChange={event => setItemForm({ ...itemForm, unit: event.target.value })}/></label>
      <label>Reorder level<input required type="number" min="0" step="0.001" value={itemForm.reorder_level} onChange={event => setItemForm({ ...itemForm, reorder_level: event.target.value })}/></label>
      <label>Unit cost (PHP)<input required type="number" min="0" step="0.01" value={itemForm.unit_cost} onChange={event => setItemForm({ ...itemForm, unit_cost: event.target.value })}/></label>
      <label>Supplier<select value={itemForm.supplier_id} onChange={event => setItemForm({ ...itemForm, supplier_id: event.target.value })}><option value="">No supplier selected</option>{supplierRows.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>
    </div><button className="primary-button" type="submit" disabled={createItem.isPending}>{createItem.isPending ? 'Saving…' : 'Create item'}</button></form>
    <form className="data-form" onSubmit={event => { event.preventDefault(); setError(''); recordMovement.mutate() }}><h2><RefreshCw size={16}/> Record stock movement</h2><div className="form-grid">
      <label>Inventory item<select required value={movement.item_id} onChange={event => setMovement({ ...movement, item_id: event.target.value })}><option value="">Choose item</option>{rows.map(row => <option key={row.id} value={row.id}>{row.name} · stock {row.quantity_on_hand}</option>)}</select></label>
      <label>Movement type<select value={movement.transaction_type} onChange={event => setMovement({ ...movement, transaction_type: event.target.value })}><option value="receipt">Receipt (+)</option><option value="issue">Issue (−)</option><option value="adjustment">Adjustment (signed)</option></select></label>
      <label>{movement.transaction_type === 'adjustment' ? 'Signed quantity delta' : 'Quantity'}<input required type="number" min={movement.transaction_type === 'adjustment' ? undefined : '0.001'} step="0.001" value={movement.quantity} onChange={event => setMovement({ ...movement, quantity: event.target.value })}/></label>
      <label>Notes<input value={movement.notes} onChange={event => setMovement({ ...movement, notes: event.target.value })}/></label>
    </div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={recordMovement.isPending || !rows.length}>{recordMovement.isPending ? 'Recording…' : 'Post stock movement'}</button></form>
    {items.isPending ? <div className="empty-state">Loading inventory…</div> : items.isError ? <div className="error-panel"><strong>Inventory unavailable</strong><p>{items.error.message}</p></div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Code</th><th>Item</th><th>Category</th><th>On hand</th><th>Reorder level</th><th>Unit cost</th><th>Status</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><strong>{row.code}</strong></td><td>{row.name}</td><td>{row.category}</td><td>{row.quantity_on_hand} {row.unit}</td><td>{row.reorder_level}</td><td>₱{Number(row.unit_cost).toFixed(2)}</td><td>{Number(row.quantity_on_hand) <= Number(row.reorder_level) ? 'Low stock' : 'In stock'}</td></tr>)}</tbody></table></div>}
    <div className="disclaimer">Low-stock alerts notify administrators and pharmacy staff. Use procurement requests and receiving for formal replenishment, rather than manually changing stock without a ledger record.</div>
  </section>
}
