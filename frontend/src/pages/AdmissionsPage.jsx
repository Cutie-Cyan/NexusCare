import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BedDouble, LogOut, MoveRight } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

export function AdmissionsPage() {
  const [form, setForm] = useState({ patient_id: '', bed_id: '', attending_doctor_id: '', admission_type: 'general' })
  const [selectedAdmissionId, setSelectedAdmissionId] = useState('')
  const [transfer, setTransfer] = useState({ to_bed_id: '', reason: '' })
  const [discharge, setDischarge] = useState({ discharge_notes: '', billing_exception_reason: '' })
  const [error, setError] = useState('')
  const client = useQueryClient()
  const admissions = useQuery({ queryKey: ['admissions'], queryFn: () => apiRequest('/admissions?limit=100') })
  const patients = useQuery({ queryKey: ['patients', 'admission-options'], queryFn: () => apiRequest('/patients?limit=100') })
  const beds = useQuery({ queryKey: ['beds', 'available'], queryFn: () => apiRequest('/beds?available_only=true') })
  const wards = useQuery({ queryKey: ['ward-overview'], queryFn: () => apiRequest('/ward-overview') })
  const create = useMutation({
    mutationFn: () => apiRequest('/admissions', { method: 'POST', body: {
      patient_id: form.patient_id, bed_id: form.bed_id || null,
      attending_doctor_id: form.attending_doctor_id || null, admission_type: form.admission_type,
    } }),
    onSuccess: () => { setForm({ patient_id: '', bed_id: '', attending_doctor_id: '', admission_type: 'general' }); setError(''); client.invalidateQueries({ queryKey: ['admissions'] }); client.invalidateQueries({ queryKey: ['beds'] }); client.invalidateQueries({ queryKey: ['ward-overview'] }) },
    onError: err => setError(err.message),
  })
  const transferPatient = useMutation({
    mutationFn: () => apiRequest('/admissions/' + selectedAdmissionId + '/transfer', { method: 'POST', body: { to_bed_id: transfer.to_bed_id, reason: transfer.reason || null } }),
    onSuccess: () => { setError(''); setTransfer({ to_bed_id: '', reason: '' }); client.invalidateQueries({ queryKey: ['admissions'] }); client.invalidateQueries({ queryKey: ['beds'] }); client.invalidateQueries({ queryKey: ['ward-overview'] }) },
    onError: err => setError(err.message),
  })
  const dischargePatient = useMutation({
    mutationFn: () => apiRequest('/admissions/' + selectedAdmissionId + '/discharge', { method: 'POST', body: {
      discharge_notes: discharge.discharge_notes,
      billing_exception_reason: discharge.billing_exception_reason || null,
    } }),
    onSuccess: () => { setError(''); setDischarge({ discharge_notes: '', billing_exception_reason: '' }); client.invalidateQueries({ queryKey: ['admissions'] }); client.invalidateQueries({ queryKey: ['beds'] }); client.invalidateQueries({ queryKey: ['ward-overview'] }); client.invalidateQueries({ queryKey: ['bills'] }) },
    onError: err => setError(err.message),
  })
  const rows = admissions.data || []
  const patientRows = patients.data || []
  const bedRows = beds.data || []
  const wardById = Object.fromEntries((wards.data || []).map(row => [row.id, row.name]))
  const patientById = Object.fromEntries(patientRows.map(row => [row.id, row]))
  const selected = rows.find(row => row.id === selectedAdmissionId)

  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">PATIENT MANAGEMENT</div><h1>Admissions</h1><p className="page-description">Admit patients, transfer beds atomically, and discharge with balance checks and audited exceptions.</p></div><span className="phase-tag">Bed locks enabled</span></div>
    <form className="data-form" onSubmit={event => { event.preventDefault(); setError(''); create.mutate() }}><h2><BedDouble size={16}/> Admit patient</h2><div className="form-grid">
      <label>Patient<select required value={form.patient_id} onChange={event => setForm({ ...form, patient_id: event.target.value })}><option value="">Choose patient</option>{patientRows.map(row => <option key={row.id} value={row.id}>{row.last_name}, {row.first_name} · {row.medical_record_number}</option>)}</select></label>
      <label>Admission type<select value={form.admission_type} onChange={event => setForm({ ...form, admission_type: event.target.value })}><option value="general">General</option><option value="emergency">Emergency</option><option value="observation">Observation</option><option value="maternity">Maternity</option><option value="surgical">Surgical</option><option value="other">Other</option></select></label>
      <label>Bed (optional)<select value={form.bed_id} onChange={event => setForm({ ...form, bed_id: event.target.value })}><option value="">No bed assigned</option>{bedRows.map(row => <option key={row.id} value={row.id}>{wardById[row.ward_id] || row.ward_id} · Bed {row.bed_number}</option>)}</select></label>
      <label>Attending doctor profile ID (optional)<input value={form.attending_doctor_id} onChange={event => setForm({ ...form, attending_doctor_id: event.target.value })} placeholder="Doctor UUID"/></label>
    </div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={create.isPending || !patientRows.length}>{create.isPending ? 'Admitting…' : 'Create admission'}</button></form>
    <div className="section-heading"><h2>Admission list</h2><span>{rows.length} RECORDS</span></div>
    {admissions.isPending ? <div className="empty-state">Loading admissions…</div> : admissions.isError ? <div className="error-panel"><strong>Admissions unavailable</strong><p>{admissions.error.message}</p></div> : rows.length === 0 ? <div className="empty-state">No admissions found.</div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Patient</th><th>Type</th><th>Bed</th><th>Status</th><th>Admitted</th><th>Actions</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><strong>{patientById[row.patient_id] ? patientById[row.patient_id].last_name + ', ' + patientById[row.patient_id].first_name : row.patient_id}</strong></td><td>{row.admission_type}</td><td>{row.bed_id || 'Unassigned'}</td><td>{row.status}</td><td>{row.admitted_at ? new Date(row.admitted_at).toLocaleString() : '—'}</td><td>{row.status === 'admitted' && <button className="table-action" onClick={() => { setSelectedAdmissionId(row.id); setError('') }}>Transfer / Discharge</button>}</td></tr>)}</tbody></table></div>}
    {selected && <section className="data-form receive-panel"><div className="section-heading"><h2>Admission actions</h2><button className="secondary-button" onClick={() => setSelectedAdmissionId('')}>Close</button></div><p className="muted-small">Admission ID: {selected.id}</p><form onSubmit={event => { event.preventDefault(); setError(''); transferPatient.mutate() }}><h3><MoveRight size={15}/> Transfer bed</h3><div className="form-grid"><label>Destination bed<select required value={transfer.to_bed_id} onChange={event => setTransfer({ ...transfer, to_bed_id: event.target.value })}><option value="">Choose available bed</option>{bedRows.filter(row => row.id !== selected.bed_id).map(row => <option key={row.id} value={row.id}>{wardById[row.ward_id] || row.ward_id} · Bed {row.bed_number}</option>)}</select></label><label>Transfer reason<input value={transfer.reason} onChange={event => setTransfer({ ...transfer, reason: event.target.value })}/></label></div><button className="secondary-button" type="submit" disabled={transferPatient.isPending || !transfer.to_bed_id}>{transferPatient.isPending ? 'Transferring…' : 'Transfer patient'}</button></form><form onSubmit={event => { event.preventDefault(); setError(''); dischargePatient.mutate() }}><h3><LogOut size={15}/> Discharge patient</h3><div className="form-grid"><label>Discharge notes<textarea required minLength="3" value={discharge.discharge_notes} onChange={event => setDischarge({ ...discharge, discharge_notes: event.target.value })}/></label><label>Administrator billing exception reason (optional)<textarea value={discharge.billing_exception_reason} onChange={event => setDischarge({ ...discharge, billing_exception_reason: event.target.value })} placeholder="Required by administrator if a balance remains"/></label></div><button className="primary-button" type="submit" disabled={dischargePatient.isPending}>{dischargePatient.isPending ? 'Discharging…' : 'Discharge patient'}</button></form>{error && <p className="form-error" role="alert">{error}</p>}</section>}
    <div className="disclaimer">Discharge checks outstanding bills. An unpaid balance requires an administrator-authorized exception reason; the exception is included in the audit trail.</div>
  </section>
}
