import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BookOpen, Plus, Search, Users, X } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const emptyForm = { medical_record_number: '', first_name: '', middle_name: '', last_name: '', date_of_birth: '', sex: '', phone: '', email: '', address: '', emergency_contact_name: '', emergency_contact_phone: '', allergies: '', notes: '' }
const dateText = value => value ? new Date(value).toLocaleString() : '—'
const textValue = value => value === null || value === undefined || value === '' ? '—' : String(value)

function HistorySection({ title, items, renderItem }) {
  return <section className="history-section"><h3>{title}<span>{items.length}</span></h3>
    {items.length ? <ul>{items.map((item, index) => <li key={item.id || item.order_id || item.result_id || index}>{renderItem(item)}</li>)}</ul> : <p className="history-empty">No records available.</p>}
  </section>
}

function PatientHistoryModal({ patient, onClose }) {
  const history = useQuery({ queryKey: ['patient-history', patient.id], queryFn: () => apiRequest('/patients/' + patient.id + '/history'), enabled: Boolean(patient.id) })
  const data = history.data || {}
  if (!patient) return null
  return <div className="modal-scrim" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <section className="history-modal" role="dialog" aria-modal="true" aria-labelledby="history-title">
      <header><div><div className="eyebrow">CONFIDENTIAL · AUTHORIZED ACCESS ONLY</div><h2 id="history-title">Patient medical history</h2><p>{patient.last_name}, {patient.first_name} · {patient.medical_record_number}</p></div><button className="icon-button" onClick={onClose} aria-label="Close history"><X size={17}/></button></header>
      {history.isPending ? <div className="empty-state">Loading authorized medical history…</div>
        : history.isError ? <div className="error-panel"><strong>History unavailable</strong><p>{history.error.message}</p></div>
        : <div className="history-content">
          <div className="history-patient-summary">
            <span><strong>DATE OF BIRTH</strong>{textValue(data.patient?.date_of_birth)}</span>
            <span><strong>SEX</strong>{textValue(data.patient?.sex)}</span>
            <span><strong>PHONE</strong>{textValue(data.patient?.phone)}</span>
            <span><strong>EMAIL</strong>{textValue(data.patient?.email)}</span>
            <span><strong>ADDRESS</strong>{textValue(data.patient?.address)}</span>
            <span><strong>EMERGENCY CONTACT</strong>{textValue(data.patient?.emergency_contact_name)}</span>
            <span><strong>EMERGENCY PHONE</strong>{textValue(data.patient?.emergency_contact_phone)}</span>
            <span><strong>ALLERGIES</strong>{textValue(data.patient?.allergies)}</span>
            <span><strong>REGISTRATION NOTES</strong>{textValue(data.patient?.notes)}</span>
          </div>
          <HistorySection title="Encounters" items={data.encounters || []} renderItem={item => <><strong>{item.encounter_type} · {item.status}</strong><span>{dateText(item.started_at)}</span><p>{textValue(item.chief_complaint)}</p></>}/>
          <HistorySection title="Diagnoses" items={data.diagnoses || []} renderItem={item => <><strong>{item.description}</strong><span>{item.code || 'No diagnosis code'}{item.is_primary ? ' · Primary' : ''}</span></>}/>
          <HistorySection title="Vital signs" items={data.vital_signs || []} renderItem={item => <><strong>{dateText(item.recorded_at)}</strong><span>BP {textValue(item.systolic_bp)}/{textValue(item.diastolic_bp)} · Pulse {textValue(item.pulse_bpm)} bpm</span><span>Temp {textValue(item.temperature_c)} °C · SpO₂ {textValue(item.oxygen_saturation)}%</span><span>Weight {textValue(item.weight_kg)} kg · Height {textValue(item.height_cm)} cm</span></>}/>
          <HistorySection title="Released lab results" items={data.released_laboratory_results || []} renderItem={item => <><strong>{item.status}</strong><span>{textValue(item.result_text)}</span>{item.result_data && <p>{JSON.stringify(item.result_data)}</p>}<span>Released {dateText(item.released_at)}</span></>}/>
          <HistorySection title="Prescriptions" items={data.prescriptions || []} renderItem={item => <><strong>{item.status}</strong><span>{textValue(item.instructions)}</span>{(item.items || []).map((medicine, index) => <p key={index}>{medicine.dose} · {medicine.route} · {medicine.frequency} · {medicine.duration} · Qty {medicine.quantity}</p>)}<span>{dateText(item.created_at)}</span></>}/>
          <HistorySection title="Admissions" items={data.admissions || []} renderItem={item => <><strong>{item.admission_type} · {item.status}</strong><span>Admitted {dateText(item.admitted_at)}</span><span>Discharged {dateText(item.discharged_at)}</span></>}/>
          <HistorySection title="Appointments" items={data.appointments || []} renderItem={item => <><strong>{item.status}</strong><span>{dateText(item.scheduled_at)}</span><p>{textValue(item.reason)}</p></>}/>
          <HistorySection title="Bills and payments" items={data.bills || []} renderItem={item => <><strong>{item.bill_number} · {item.status}</strong><span>Total ₱{Number(item.total || 0).toFixed(2)}</span>{(item.payments || []).map(payment => <p key={payment.id}>₱{Number(payment.amount || 0).toFixed(2)} · {payment.payment_method} · {payment.status} · {payment.receipt_number || 'No receipt'}</p>)}</>}/>
        </div>}
    </section>
  </div>
}

export function PatientsPage({ roles = [] }) {
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [selectedPatient, setSelectedPatient] = useState(null)
  const [editingPatientId, setEditingPatientId] = useState('')
  const canRegister = roles.some(role => ['administrator', 'information_officer'].includes(role))
  const queryClient = useQueryClient()
  const patientsQuery = useQuery({ queryKey: ['patients', search], queryFn: () => apiRequest('/patients?limit=100' + (search.trim() ? '&q=' + encodeURIComponent(search.trim()) : '')) })
  const createPatient = useMutation({
    mutationFn: values => {
      const payload = { ...values, date_of_birth: values.date_of_birth || null }
      if (editingPatientId) {
        delete payload.medical_record_number
        return apiRequest('/patients/' + editingPatientId, { method: 'PATCH', body: payload })
      }
      return apiRequest('/patients', { method: 'POST', body: payload })
    },
    onSuccess: () => { setForm(emptyForm); setEditingPatientId(''); setShowForm(false); setFormError(''); queryClient.invalidateQueries({ queryKey: ['patients'] }) },
    onError: error => setFormError(error.message || 'Could not register patient.'),
  })
  function submit(event) { event.preventDefault(); setFormError(''); createPatient.mutate(form) }
  const patients = patientsQuery.data || []
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">PATIENT MANAGEMENT</div><h1>Patients</h1><p className="page-description">Search authorized patient records, register patients, and open a role-scoped medical history.</p></div>{canRegister && <button className="primary-button page-action" onClick={() => { setShowForm(value => !value); setEditingPatientId(''); setForm(emptyForm); setFormError('') }}><Plus size={16}/>{showForm ? 'Close form' : 'Register patient'}</button>}</div>
    {showForm && canRegister && <form className="data-form" onSubmit={submit}><h2>{editingPatientId ? 'Edit patient demographics' : 'Register patient'}</h2><div className="form-grid">
      {!editingPatientId && <label>Medical record number<input required minLength="2" maxLength="40" value={form.medical_record_number} onChange={event => setForm({ ...form, medical_record_number: event.target.value })} placeholder="MRN-00021"/></label>}
      <label>First name<input required value={form.first_name} onChange={event => setForm({ ...form, first_name: event.target.value })}/></label>
      <label>Middle name<input value={form.middle_name} onChange={event => setForm({ ...form, middle_name: event.target.value })}/></label>
      <label>Last name<input required value={form.last_name} onChange={event => setForm({ ...form, last_name: event.target.value })}/></label>
      <label>Date of birth<input type="date" value={form.date_of_birth} onChange={event => setForm({ ...form, date_of_birth: event.target.value })}/></label>
      <label>Sex<select value={form.sex} onChange={event => setForm({ ...form, sex: event.target.value })}><option value="">Select sex</option><option value="Female">Female</option><option value="Male">Male</option><option value="Other">Other</option><option value="Not specified">Prefer not to say</option></select></label>
      <label>Phone<input value={form.phone} onChange={event => setForm({ ...form, phone: event.target.value })}/></label>
      <label>Email<input type="email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })}/></label>
      <label>Address<input value={form.address} onChange={event => setForm({ ...form, address: event.target.value })}/></label>
      <label>Emergency contact<input value={form.emergency_contact_name} onChange={event => setForm({ ...form, emergency_contact_name: event.target.value })}/></label>
      <label>Emergency contact phone<input value={form.emergency_contact_phone} onChange={event => setForm({ ...form, emergency_contact_phone: event.target.value })}/></label>
      <label>Allergies<input value={form.allergies} onChange={event => setForm({ ...form, allergies: event.target.value })} placeholder="Document known allergies"/></label>
      <label className="form-grid-full">Notes<textarea rows="2" value={form.notes} onChange={event => setForm({ ...form, notes: event.target.value })}/></label>
    </div>{formError && <p className="form-error" role="alert">{formError}</p>}<button className="primary-button" type="submit" disabled={createPatient.isPending}>{createPatient.isPending ? 'Saving…' : editingPatientId ? 'Save changes' : 'Save patient'}</button></form>}
    <div className="table-toolbar"><div className="search-field"><Search size={16}/><input aria-label="Search patients" value={search} onChange={event => setSearch(event.target.value)} placeholder="Search name or medical record number"/></div><span>{patients.length} record{patients.length === 1 ? '' : 's'}</span></div>
    {patientsQuery.isPending ? <div className="empty-state">Loading patient records…</div>
      : patientsQuery.isError ? <div className="error-panel"><strong>Could not load patients</strong><p>{patientsQuery.error.message}</p><p>Sign in with an account that has patient-read permissions, and confirm the backend is running.</p></div>
      : patients.length === 0 ? <div className="empty-state"><Users size={24}/><strong>No patients found</strong><span>Try another search or register a new patient if your role allows it.</span></div>
      : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Medical record no.</th><th>Patient name</th><th>Date of birth</th><th>Sex</th><th>Phone</th><th>Actions</th></tr></thead><tbody>{patients.map(patient => <tr key={patient.id}><td><strong>{patient.medical_record_number}</strong></td><td>{[patient.last_name, patient.first_name, patient.middle_name].filter(Boolean).join(', ')}</td><td>{patient.date_of_birth || '—'}</td><td>{patient.sex || '—'}</td><td>{patient.phone || '—'}</td><td>{canRegister && <button className="table-action" onClick={() => { setEditingPatientId(patient.id); setForm({ ...emptyForm, ...patient, date_of_birth: patient.date_of_birth || '', middle_name: patient.middle_name || '', sex: patient.sex || '', phone: patient.phone || '', email: patient.email || '', address: patient.address || '', emergency_contact_name: patient.emergency_contact_name || '', emergency_contact_phone: patient.emergency_contact_phone || '', allergies: patient.allergies || '', notes: patient.notes || '' }); setShowForm(true); setFormError('') }}>Edit</button>} <button className="table-action" onClick={() => setSelectedPatient(patient)}><BookOpen size={13}/> View history</button></td></tr>)}</tbody></table></div>}
    {selectedPatient && <PatientHistoryModal patient={selectedPatient} onClose={() => setSelectedPatient(null)}/>}
  </section>
}
