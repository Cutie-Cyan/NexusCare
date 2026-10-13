import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Plus, Search, Users } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const emptyForm = { medical_record_number: '', first_name: '', last_name: '', date_of_birth: '', sex: '', phone: '', email: '' }

export function PatientsPage() {
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const queryClient = useQueryClient()
  const patientsQuery = useQuery({ queryKey: ['patients', search], queryFn: () => apiRequest(`/patients?limit=100${search.trim() ? `&q=${encodeURIComponent(search.trim())}` : ''}`) })
  const createPatient = useMutation({
    mutationFn: values => apiRequest('/patients', { method: 'POST', body: { ...values, date_of_birth: values.date_of_birth || null, sex: values.sex || null, phone: values.phone || null, email: values.email || null } }),
    onSuccess: () => { setForm(emptyForm); setShowForm(false); setFormError(''); queryClient.invalidateQueries({ queryKey: ['patients'] }) },
    onError: error => setFormError(error.message || 'Could not register patient.'),
  })
  function submit(event) { event.preventDefault(); setFormError(''); createPatient.mutate(form) }
  const patients = patientsQuery.data || []
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">PATIENT MANAGEMENT</div><h1>Patients</h1><p className="page-description">Search authorized patient records and register new patients. The API enforces role permissions.</p></div><button className="primary-button page-action" onClick={() => setShowForm(value => !value)}><Plus size={16}/>{showForm ? 'Close form' : 'Register patient'}</button></div>
    {showForm && <form className="data-form" onSubmit={submit}><h2>Register patient</h2><div className="form-grid">
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
      : patientsQuery.isError ? <div className="error-panel"><strong>Could not load patients</strong><p>{patientsQuery.error.message}</p><p>Sign in with a staff account that has patient-read permissions, and confirm the backend is running.</p></div>
      : patients.length === 0 ? <div className="empty-state"><Users size={24}/><strong>No patients found</strong><span>Try another search or register a new patient if your role allows it.</span></div>
      : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Medical record no.</th><th>Patient name</th><th>Date of birth</th><th>Sex</th><th>Phone</th></tr></thead><tbody>{patients.map(patient => <tr key={patient.id}><td><strong>{patient.medical_record_number}</strong></td><td>{[patient.last_name, patient.first_name, patient.middle_name].filter(Boolean).join(', ')}</td><td>{patient.date_of_birth || '—'}</td><td>{patient.sex || '—'}</td><td>{patient.phone || '—'}</td></tr>)}</tbody></table></div>}
  </section>
}
