import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CalendarPlus, Video } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const emptyForm = { patient_id: '', department_id: '', clinician_id: '', scheduled_at: '', reason: '' }

export function AppointmentsPage({ roles = [] }) {
  const isPatient = roles.includes('patient') && !roles.some(role => ['administrator', 'information_officer', 'doctor', 'nurse'].includes(role))
  const canCreate = isPatient || roles.some(role => ['administrator', 'information_officer', 'doctor', 'nurse'].includes(role))
  const [form, setForm] = useState(emptyForm)
  const [error, setError] = useState('')
  const client = useQueryClient()
  const appointments = useQuery({ queryKey: ['appointments'], queryFn: () => apiRequest('/appointments?limit=100') })
  const patients = useQuery({ queryKey: ['patients', 'appointment-options'], queryFn: () => apiRequest('/patients?limit=100'), enabled: !isPatient })
  const departments = useQuery({ queryKey: ['departments'], queryFn: () => apiRequest('/departments'), enabled: !isPatient })
  const schedules = useQuery({ queryKey: ['doctor-schedules'], queryFn: () => apiRequest('/doctor-schedules'), enabled: !isPatient })
  const create = useMutation({
    mutationFn: () => apiRequest('/appointments', { method: 'POST', body: {
      ...(isPatient ? {} : { patient_id: form.patient_id }),
      department_id: form.department_id || null, clinician_id: form.clinician_id || null,
      scheduled_at: new Date(form.scheduled_at).toISOString(), reason: form.reason || null,
    } }),
    onSuccess: () => { setForm(emptyForm); setError(''); client.invalidateQueries({ queryKey: ['appointments'] }) },
    onError: err => setError(err.message),
  })
  const updateStatus = useMutation({
    mutationFn: ({ id, status }) => apiRequest('/appointments/' + id + '/status', { method: 'PATCH', body: { status } }),
    onSuccess: () => { setError(''); client.invalidateQueries({ queryKey: ['appointments'] }) },
    onError: err => setError(err.message),
  })
  const requestOnline = useMutation({
    mutationFn: id => apiRequest('/appointments/' + id + '/request-online-consultation', { method: 'POST' }),
    onSuccess: () => { setError(''); client.invalidateQueries({ queryKey: ['online-consultations'] }) },
    onError: err => setError(err.message),
  })
  const patientRows = patients.data || []
  const patientById = Object.fromEntries(patientRows.map(row => [row.id, row]))
  const appointmentRows = appointments.data || []
  const doctorIds = [...new Set((schedules.data || []).map(row => row.doctor_id))]
  const doctors = doctorIds.map(id => ({ id, name: (schedules.data || []).find(row => row.doctor_id === id)?.doctor_name || id }))

  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">HOSPITAL OPERATIONS</div><h1>Appointments</h1><p className="page-description">{isPatient ? 'Request or cancel your own appointment and request an online consultation.' : 'Schedule patients, manage appointment status, and request online consultation sessions.'}</p></div><span className="phase-tag">Live API</span></div>
    {canCreate && <form className="data-form" onSubmit={event => { event.preventDefault(); setError(''); create.mutate() }}>
      <h2><CalendarPlus size={16}/> {isPatient ? 'Request appointment' : 'Schedule appointment'}</h2><div className="form-grid">
        {!isPatient && <label>Patient<select required value={form.patient_id} onChange={event => setForm({ ...form, patient_id: event.target.value })}><option value="">Choose patient</option>{patientRows.map(row => <option key={row.id} value={row.id}>{row.last_name}, {row.first_name} · {row.medical_record_number}</option>)}</select></label>}
        {!isPatient && <label>Department<select value={form.department_id} onChange={event => setForm({ ...form, department_id: event.target.value })}><option value="">No department selected</option>{(departments.data || []).map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>}
        {!isPatient && <label>Clinician<select value={form.clinician_id} onChange={event => setForm({ ...form, clinician_id: event.target.value })}><option value="">Assign later</option>{doctors.map(row => <option key={row.id} value={row.id}>{row.name}</option>)}</select></label>}
        <label>Date and time<input required type="datetime-local" min={new Date(Date.now() + 60000).toISOString().slice(0, 16)} value={form.scheduled_at} onChange={event => setForm({ ...form, scheduled_at: event.target.value })}/></label>
        <label>Reason / notes<input maxLength="2000" value={form.reason} onChange={event => setForm({ ...form, reason: event.target.value })} placeholder="Optional reason for appointment"/></label>
      </div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={create.isPending || (!isPatient && !patientRows.length)}>{create.isPending ? 'Saving…' : isPatient ? 'Request appointment' : 'Schedule appointment'}</button>
    </form>}
    {appointments.isPending ? <div className="empty-state">Loading appointments…</div> : appointments.isError ? <div className="error-panel"><strong>Appointments unavailable</strong><p>{appointments.error.message}</p></div> : appointmentRows.length === 0 ? <div className="empty-state">No appointments found.</div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Scheduled</th><th>Patient</th><th>Clinician</th><th>Status</th><th>Reason</th><th>Actions</th></tr></thead><tbody>{appointmentRows.map(row => <tr key={row.id}><td>{new Date(row.scheduled_at).toLocaleString()}</td><td>{patientById[row.patient_id] ? patientById[row.patient_id].last_name + ', ' + patientById[row.patient_id].first_name : row.patient_id}</td><td>{doctors.find(doctor => doctor.id === row.clinician_id)?.name || row.clinician_id || 'Unassigned'}</td><td>{row.status}</td><td>{row.reason || '—'}</td><td><div className="row-actions">{isPatient ? row.status === 'scheduled' || row.status === 'confirmed' ? <button className="table-action" onClick={() => updateStatus.mutate({ id: row.id, status: 'cancelled' })}>Cancel</button> : null : row.status === 'scheduled' && <button className="table-action" onClick={() => updateStatus.mutate({ id: row.id, status: 'confirmed' })}>Confirm</button>}{!isPatient && row.status === 'confirmed' && <button className="table-action" onClick={() => updateStatus.mutate({ id: row.id, status: 'checked_in' })}>Check in</button>}{!isPatient && ['confirmed', 'checked_in'].includes(row.status) && <button className="table-action" onClick={() => updateStatus.mutate({ id: row.id, status: 'completed' })}>Complete</button>}{['scheduled', 'confirmed'].includes(row.status) && <button className="table-action" onClick={() => requestOnline.mutate(row.id)} disabled={requestOnline.isPending}><Video size={13}/> Online consult</button>}</div></td></tr>)}</tbody></table></div>}
    {error && !canCreate && <p className="form-error" role="alert">{error}</p>}
    <div className="disclaimer">Appointment times are converted to UTC before submission. When a clinician has active schedules configured, the backend checks the requested time against those schedules and rejects exact-time conflicts.</div>
  </section>
}
