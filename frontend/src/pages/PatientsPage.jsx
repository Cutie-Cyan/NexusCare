import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Eye, Plus, Search, Users, X } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const emptyForm = { medical_record_number: '', first_name: '', last_name: '', date_of_birth: '', sex: '', phone: '', email: '' }

function HistoryList({ title, rows, render }) {
  return <section className="history-section"><h3>{title} <span>{rows?.length || 0}</span></h3>{!rows?.length ? <p className="history-empty">No records available.</p> : <ul>{rows.map((row, index) => <li key={row.id || row.order_id || row.receipt_number || index}>{render(row)}</li>)}</ul>}</section>
}

export function PatientsPage({ roles = [] }) {
  const canRegister = roles.some(role => ['administrator', 'information_officer'].includes(role))
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [selectedPatient, setSelectedPatient] = useState(null)
  const queryClient = useQueryClient()
  const patientsQuery = useQuery({ queryKey: ['patients', search], queryFn: () => apiRequest(`/patients?limit=100${search.trim() ? `&q=${encodeURIComponent(search.trim())}` : ''}`) })
  const historyQuery = useQuery({
    queryKey: ['patient-history', selectedPatient?.id],
    queryFn: () => apiRequest(`/patients/${selectedPatient.id}/history`),
    enabled: Boolean(selectedPatient?.id),
  })
  const createPatient = useMutation({
    mutationFn: values => apiRequest('/patients', { method: 'POST', body: {
      ...values,
      date_of_birth: values.date_of_birth || null,
      sex: values.sex || null,
      phone: values.phone || null,
      email: values.email || null,
    } }),
    onSuccess: () => {
      setForm(emptyForm)
      setShowForm(false)
      setFormError('')
      queryClient.invalidateQueries({ queryKey: ['patients'] })
    },
    onError: error => setFormError(error.message || 'Could not register patient.'),
  })

  function submit(event) { event.preventDefault(); setFormError(''); createPatient.mutate(form) }
  const patients = patientsQuery.data || []
  const history = historyQuery.data
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">PATIENT MANAGEMENT</div><h1>Patients</h1><p className="page-description">Search permitted patient records, open the consolidated history, and register patients if your role allows it.</p></div>{canRegister && <button className="primary-button page-action" onClick={() => setShowForm(value => !value)}><Plus size={16}/>{showForm ? 'Close form' : 'Register patient'}</button>}</div>
    {showForm && canRegister && <form className="data-form" onSubmit={submit}><h2>Register patient</h2><div className="form-grid">
      <label>Medical record number<input required minLength="2" maxLength="40" value={form.medical_record_number} onChange={event => setForm({ ...form, medical_record_number: event.target.value })} placeholder="MRN-00021"/></label>
      <label>First name<input required value={form.first_name} onChange={event => setForm({ ...form, first_name: event.target.value })}/></label>
      <label>Last name<input required value={form.last_name} onChange={event => setForm({ ...form, last_name: event.target.value })}/></label>
      <label>Date of birth<input type="date" value={form.date_of_birth} onChange={event => setForm({ ...form, date_of_birth: event.target.value })}/></label>
      <label>Sex<input value={form.sex} onChange={event => setForm({ ...form, sex: event.target.value })} placeholder="Optional"/></label>
      <label>Phone<input value={form.phone} onChange={event => setForm({ ...form, phone: event.target.value })}/></label>
      <label>Email<input type="email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })}/></label>
    </div>{formError && <p className="form-error" role="alert">{formError}</p>}<button className="primary-button" type="submit" disabled={createPatient.isPending}>{createPatient.isPending ? 'Saving…' : 'Save patient'}</button></form>}
    <div className="table-toolbar"><div className="search-field"><Search size={16}/><input aria-label="Search patients" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search name or medical record number"/></div><span>{patients.length} record{patients.length === 1 ? '' : 's'}</span></div>
    {patientsQuery.isPending ? <div className="empty-state">Loading patient records…</div>
      : patientsQuery.isError ? <div className="error-panel"><strong>Could not load patients</strong><p>{patientsQuery.error.message}</p><p>Sign in with an account that has patient-read permissions, and confirm the backend is running.</p></div>
      : patients.length === 0 ? <div className="empty-state"><Users size={24}/><strong>No patients found</strong><span>Try another search or register a patient if your role allows it.</span></div>
      : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Medical record no.</th><th>Patient name</th><th>Date of birth</th><th>Sex</th><th>Phone</th><th>History</th></tr></thead><tbody>{patients.map(patient => <tr key={patient.id}><td><strong>{patient.medical_record_number}</strong></td><td>{[patient.last_name, patient.first_name, patient.middle_name].filter(Boolean).join(', ')}</td><td>{patient.date_of_birth || '—'}</td><td>{patient.sex || '—'}</td><td>{patient.phone || '—'}</td><td><button className="table-action" onClick={() => setSelectedPatient(patient)}><Eye size={14}/> View</button></td></tr>)}</tbody></table></div>}
    {selectedPatient && <div className="modal-scrim" onClick={() => setSelectedPatient(null)}><section className="history-modal" role="dialog" aria-modal="true" aria-label="Patient medical history" onClick={event => event.stopPropagation()}>
      <header><div><span className="eyebrow">PATIENT HISTORY</span><h2>{selectedPatient.last_name}, {selectedPatient.first_name}</h2><p>{selectedPatient.medical_record_number}</p></div><button className="icon-button" aria-label="Close history" onClick={() => setSelectedPatient(null)}><X size={18}/></button></header>
      {historyQuery.isPending ? <div className="empty-state">Loading consolidated medical history…</div>
        : historyQuery.isError ? <div className="error-panel"><strong>History unavailable</strong><p>{historyQuery.error.message}</p></div>
        : <div className="history-content">
          <div className="history-patient-summary"><span><strong>Allergies</strong>{history?.patient?.allergies || 'None recorded'}</span><span><strong>Contact</strong>{history?.patient?.phone || 'Not recorded'}</span></div>
          <HistoryList title="Encounters" rows={history?.encounters} render={row => <><strong>{row.encounter_type}</strong><span>{row.status} · {row.started_at ? new Date(row.started_at).toLocaleString() : 'Date unavailable'}</span>{row.chief_complaint && <p>{row.chief_complaint}</p>}</>}/>
          <HistoryList title="Diagnoses" rows={history?.diagnoses} render={row => <><strong>{row.description}</strong><span>{row.code || 'No code'}{row.is_primary ? ' · Primary' : ''}</span></>}/>
          <HistoryList title="Vital signs" rows={history?.vital_signs} render={row => <><strong>{row.recorded_at ? new Date(row.recorded_at).toLocaleString() : 'Recorded vitals'}</strong><span>{[row.temperature_c != null && `Temp ${row.temperature_c}°C`, row.pulse_bpm != null && `Pulse ${row.pulse_bpm}`, row.systolic_bp != null && row.diastolic_bp != null && `BP ${row.systolic_bp}/${row.diastolic_bp}`, row.oxygen_saturation != null && `SpO₂ ${row.oxygen_saturation}%`].filter(Boolean).join(' · ') || 'No values recorded'}</span></>}/>
          <HistoryList title="Released laboratory results" rows={history?.released_laboratory_results} render={row => <><strong>{row.result_text || 'Structured result'}</strong><span>Order {row.order_id} · Released {row.released_at ? new Date(row.released_at).toLocaleString() : 'date unavailable'}</span></>}/>
          <HistoryList title="Prescriptions" rows={history?.prescriptions} render={row => <><strong>{row.status}</strong><span>{row.created_at ? new Date(row.created_at).toLocaleString() : ''}</span>{row.instructions && <p>{row.instructions}</p>}</>}/>
          <HistoryList title="Admissions" rows={history?.admissions} render={row => <><strong>{row.admission_type} · {row.status}</strong><span>Admitted {row.admitted_at ? new Date(row.admitted_at).toLocaleString() : 'date unavailable'}</span></>}/>
          <HistoryList title="Appointments" rows={history?.appointments} render={row => <><strong>{row.status}</strong><span>{new Date(row.scheduled_at).toLocaleString()}</span>{row.reason && <p>{row.reason}</p>}</>}/>
          {history?.bills && <HistoryList title="Bills and payments" rows={history.bills} render={row => <><strong>{row.bill_number} · ₱{Number(row.total).toFixed(2)}</strong><span>{row.status} · {row.payments?.length || 0} payment record(s)</span></>}/>}
        </div>}
    </section></div>}
  </section>
}
