import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Siren } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const triageLevels = ['red', 'orange', 'yellow', 'green', 'blue']

export function EmergencyPage({ roles = [] }) {
  const canTriage = roles.some(role => ['doctor', 'nurse'].includes(role))
  const canRegister = roles.some(role => ['administrator', 'information_officer', 'doctor', 'nurse'].includes(role))
  const [form, setForm] = useState({ patient_id: '', triage_level: 'yellow', chief_complaint: '' })
  const [selectedId, setSelectedId] = useState('')
  const [triage, setTriage] = useState({ triage_level: 'yellow', status: 'waiting' })
  const [error, setError] = useState('')
  const client = useQueryClient()
  const events = useQuery({ queryKey: ['emergency-events'], queryFn: () => apiRequest('/emergency-events?limit=100') })
  const patients = useQuery({ queryKey: ['patients', 'emergency-options'], queryFn: () => apiRequest('/patients?limit=100'), enabled: canRegister })
  const create = useMutation({
    mutationFn: () => apiRequest('/emergency-events', { method: 'POST', body: { ...form, status: 'waiting' } }),
    onSuccess: () => { setForm({ patient_id: '', triage_level: 'yellow', chief_complaint: '' }); setError(''); client.invalidateQueries({ queryKey: ['emergency-events'] }) },
    onError: err => setError(err.message),
  })
  const updateTriage = useMutation({
    mutationFn: () => apiRequest('/emergency-events/' + selectedId + '/triage', { method: 'PATCH', body: triage }),
    onSuccess: () => { setError(''); client.invalidateQueries({ queryKey: ['emergency-events'] }) },
    onError: err => setError(err.message),
  })
  const patientRows = patients.data || []
  const patientById = Object.fromEntries(patientRows.map(row => [row.id, row]))
  const rows = events.data || []
  const selected = rows.find(row => row.id === selectedId)
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">PATIENT MANAGEMENT</div><h1>Emergency Room</h1><p className="page-description">Register emergency events and maintain triage priority with an auditable status history.</p></div><span className="phase-tag">Triage queue</span></div>
    {canRegister && <form className="data-form" onSubmit={event => { event.preventDefault(); setError(''); create.mutate() }}><h2><Siren size={16}/> Register emergency event</h2><div className="form-grid">
      <label>Patient (optional for unidentified emergency)<select value={form.patient_id} onChange={event => setForm({ ...form, patient_id: event.target.value })}><option value="">Unidentified / not linked yet</option>{patientRows.map(row => <option key={row.id} value={row.id}>{row.last_name}, {row.first_name} · {row.medical_record_number}</option>)}</select></label>
      <label>Triage level<select value={form.triage_level} onChange={event => setForm({ ...form, triage_level: event.target.value })}>{triageLevels.map(level => <option key={level} value={level}>{level.toUpperCase()}</option>)}</select></label>
      <label>Chief complaint<textarea required minLength="2" maxLength="5000" rows="3" value={form.chief_complaint} onChange={event => setForm({ ...form, chief_complaint: event.target.value })}/></label>
    </div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={create.isPending}>{create.isPending ? 'Registering…' : 'Register emergency'}</button></form>}
    {events.isPending ? <div className="empty-state">Loading emergency queue…</div> : events.isError ? <div className="error-panel"><strong>Emergency queue unavailable</strong><p>{events.error.message}</p></div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Event</th><th>Patient</th><th>Complaint</th><th>Triage</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><strong>{row.id}</strong></td><td>{patientById[row.patient_id] ? patientById[row.patient_id].last_name + ', ' + patientById[row.patient_id].first_name : row.patient_id || 'Unidentified'}</td><td>{row.chief_complaint}</td><td><span className={'triage-label triage-' + row.triage_level}>{row.triage_level?.toUpperCase()}</span></td><td>{row.status}</td><td>{canTriage && <button className="table-action" onClick={() => { setSelectedId(row.id); setTriage({ triage_level: row.triage_level, status: row.status }); setError('') }}>Update triage</button>}</td></tr>)}</tbody></table></div>}
    {selected && canTriage && <section className="data-form receive-panel"><h2>Update triage</h2><form onSubmit={event => { event.preventDefault(); setError(''); updateTriage.mutate() }}><div className="form-grid"><label>Triage level<select value={triage.triage_level} onChange={event => setTriage({ ...triage, triage_level: event.target.value })}>{triageLevels.map(level => <option key={level} value={level}>{level.toUpperCase()}</option>)}</select></label><label>Status<select value={triage.status} onChange={event => setTriage({ ...triage, status: event.target.value })}><option value="waiting">Waiting</option><option value="in_treatment">In treatment</option><option value="transferred">Transferred</option><option value="completed">Completed</option></select></label></div><div className="row-actions"><button className="primary-button" type="submit" disabled={updateTriage.isPending}>{updateTriage.isPending ? 'Saving…' : 'Save triage'}</button><button className="secondary-button" type="button" onClick={() => setSelectedId('')}>Close</button></div></form>{error && <p className="form-error" role="alert">{error}</p>}</section>}
    <div className="disclaimer">Triage is a clinical decision. Use the triage colors defined by your project policy and fictional demo cases only.</div>
  </section>
}
