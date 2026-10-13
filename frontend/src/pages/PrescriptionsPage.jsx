import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FilePlus2, Pill } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const empty = { encounter_id: '', medicine_id: '', dose: '', route: 'oral', frequency: '', duration: '', quantity: '1', instructions: '', prescription_instructions: '' }

export function PrescriptionsPage({ roles = [] }) {
  const canPrescribe = roles.includes('doctor')
  const [form, setForm] = useState(empty)
  const [selectedPrescriptionId, setSelectedPrescriptionId] = useState('')
  const [error, setError] = useState('')
  const client = useQueryClient()
  const prescriptions = useQuery({ queryKey: ['prescriptions'], queryFn: () => apiRequest('/prescriptions?limit=100') })
  const encounters = useQuery({ queryKey: ['encounters', 'prescription-options'], queryFn: () => apiRequest('/encounters?limit=100'), enabled: canPrescribe })
  const medicines = useQuery({ queryKey: ['medicines'], queryFn: () => apiRequest('/medicines') })
  const items = useQuery({
    queryKey: ['prescription-items', selectedPrescriptionId],
    queryFn: () => apiRequest('/prescriptions/' + selectedPrescriptionId + '/items'),
    enabled: Boolean(selectedPrescriptionId),
  })
  const create = useMutation({
    mutationFn: () => apiRequest('/prescriptions', { method: 'POST', body: {
      encounter_id: form.encounter_id, instructions: form.prescription_instructions || null,
      items: [{
        medicine_id: form.medicine_id, dose: form.dose, route: form.route || null,
        frequency: form.frequency, duration: form.duration || null,
        quantity: Number(form.quantity), instructions: form.instructions || null,
      }],
    } }),
    onSuccess: () => { setForm(empty); setError(''); client.invalidateQueries({ queryKey: ['prescriptions'] }) },
    onError: err => setError(err.message),
  })
  const prescriptionRows = prescriptions.data || []
  const encounterRows = encounters.data || []
  const medicineRows = medicines.data || []
  const itemRows = items.data || []

  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">CLINICAL SERVICES</div><h1>Prescriptions</h1><p className="page-description">Doctors can issue prescriptions for open encounters; pharmacy staff can review items and dispense from valid batches.</p></div><span className="phase-tag">Role controlled</span></div>
    {canPrescribe && <form className="data-form" onSubmit={event => { event.preventDefault(); setError(''); create.mutate() }}>
      <h2><FilePlus2 size={16}/> Issue prescription</h2><div className="form-grid">
        <label>Encounter<select required value={form.encounter_id} onChange={event => setForm({ ...form, encounter_id: event.target.value })}><option value="">Choose open encounter</option>{encounterRows.filter(row => row.status === 'open').map(row => <option key={row.id} value={row.id}>{row.id} · {row.encounter_type} · {row.patient_id}</option>)}</select></label>
        <label>Medicine<select required value={form.medicine_id} onChange={event => setForm({ ...form, medicine_id: event.target.value })}><option value="">Choose medicine</option>{medicineRows.filter(row => row.is_active).map(row => <option key={row.id} value={row.id}>{row.name} {row.strength || ''} · {row.dosage_form || ''}</option>)}</select></label>
        <label>Dose<input required maxLength="120" value={form.dose} onChange={event => setForm({ ...form, dose: event.target.value })} placeholder="1 tablet"/></label>
        <label>Route<select value={form.route} onChange={event => setForm({ ...form, route: event.target.value })}><option value="oral">Oral</option><option value="topical">Topical</option><option value="inhalation">Inhalation</option><option value="injection">Injection</option><option value="other">Other</option></select></label>
        <label>Frequency<input required maxLength="120" value={form.frequency} onChange={event => setForm({ ...form, frequency: event.target.value })} placeholder="3 times daily"/></label>
        <label>Duration<input maxLength="120" value={form.duration} onChange={event => setForm({ ...form, duration: event.target.value })} placeholder="5 days"/></label>
        <label>Quantity<input required type="number" min="1" max="10000" step="1" value={form.quantity} onChange={event => setForm({ ...form, quantity: event.target.value })}/></label>
        <label>Item instructions<input maxLength="2000" value={form.instructions} onChange={event => setForm({ ...form, instructions: event.target.value })}/></label>
        <label>Prescription notes<input maxLength="5000" value={form.prescription_instructions} onChange={event => setForm({ ...form, prescription_instructions: event.target.value })}/></label>
      </div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={create.isPending || !medicineRows.length || !encounterRows.length}>{create.isPending ? 'Saving…' : 'Issue prescription'}</button>
    </form>}
    <div className="section-heading"><h2>Prescription records</h2><span>{prescriptionRows.length} RECORDS</span></div>
    {prescriptions.isPending ? <div className="empty-state">Loading prescriptions…</div> : prescriptions.isError ? <div className="error-panel"><strong>Prescriptions unavailable</strong><p>{prescriptions.error.message}</p></div> : prescriptionRows.length === 0 ? <div className="empty-state"><Pill size={22}/>No prescriptions found.</div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Prescription</th><th>Encounter</th><th>Issued</th><th>Status</th><th>Notes</th><th>Items</th></tr></thead><tbody>{prescriptionRows.map(row => <tr key={row.id}><td><strong>{row.id}</strong></td><td>{row.encounter_id}</td><td>{row.created_at ? new Date(row.created_at).toLocaleString() : '—'}</td><td>{row.status}</td><td>{row.instructions || '—'}</td><td><button className="table-action" onClick={() => setSelectedPrescriptionId(current => current === row.id ? '' : row.id)}>View items</button></td></tr>)}</tbody></table></div>}
    {selectedPrescriptionId && <section className="data-form receive-panel"><h2>Prescription items</h2>{items.isPending ? <p>Loading items…</p> : items.isError ? <p className="form-error">{items.error.message}</p> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Medicine ID</th><th>Dose</th><th>Route</th><th>Frequency</th><th>Duration</th><th>Quantity</th><th>Instructions</th></tr></thead><tbody>{itemRows.map(row => <tr key={row.id}><td>{medicineRows.find(medicine => medicine.id === row.medicine_id)?.name || row.medicine_id}</td><td>{row.dose}</td><td>{row.route || '—'}</td><td>{row.frequency}</td><td>{row.duration || '—'}</td><td>{row.quantity}</td><td>{row.instructions || '—'}</td></tr>)}</tbody></table></div>}</section>}
    <div className="disclaimer">Prescription creation is doctor-only. Pharmacy dispensing is a separate workflow that validates batch expiry, available stock, and the remaining prescribed quantity.</div>
  </section>
}
