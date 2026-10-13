import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { UserPlus, Users } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const availableRoles = [
  ['administrator', 'Administrator'], ['information_officer', 'Information Officer'],
  ['doctor', 'Doctor'], ['nurse', 'Nurse'], ['cashier', 'Cashier'],
  ['laboratory_staff', 'Laboratory Staff'], ['pharmacy_staff', 'Pharmacy Staff'], ['patient', 'Patient'],
]

const initialForm = { full_name: '', email: '', initial_password: '', department_id: '', patient_id: '' }

export function StaffPage() {
  const [form, setForm] = useState(initialForm)
  const [roleCodes, setRoleCodes] = useState(['doctor'])
  const [error, setError] = useState('')
  const queryClient = useQueryClient()
  const staff = useQuery({ queryKey: ['staff'], queryFn: () => apiRequest('/admin/staff?limit=200') })
  const create = useMutation({
    mutationFn: () => apiRequest('/admin/staff', { method: 'POST', body: {
      full_name: form.full_name.trim(), email: form.email.trim(),
      initial_password: form.initial_password, role_codes: roleCodes,
      department_id: form.department_id.trim() || null,
      patient_id: roleCodes.includes('patient') ? (form.patient_id.trim() || null) : null,
    } }),
    onSuccess: () => {
      setForm(initialForm)
      setRoleCodes(['doctor'])
      setError('')
      queryClient.invalidateQueries({ queryKey: ['staff'] })
    },
    onError: err => setError(err.message || 'Account creation failed.'),
  })

  function toggleRole(role, checked) {
    if (role === 'patient') { setRoleCodes(checked ? ['patient'] : []); return }
    setRoleCodes(current => {
      const withoutPatient = current.filter(item => item !== 'patient')
      return checked ? [...new Set([...withoutPatient, role])] : withoutPatient.filter(item => item !== role)
    })
  }

  function submit(event) {
    event.preventDefault()
    setError('')
    if (roleCodes.length === 0) { setError('Choose at least one role.'); return }
    if (roleCodes.includes('patient') && !form.patient_id.trim()) { setError('Patient accounts must be linked to an existing patient ID.'); return }
    create.mutate()
  }

  const rows = staff.data || []
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">ADMINISTRATION</div><h1>Staff & Accounts</h1><p className="page-description">Provision Supabase Auth users and assign NexusCare roles. Only administrators can access this screen.</p></div><span className="phase-tag">Admin only</span></div>
    <form className="data-form" onSubmit={submit}>
      <h2><UserPlus size={16}/> Create account</h2>
      <div className="form-grid">
        <label>Full name<input required minLength="2" maxLength="180" value={form.full_name} onChange={event => setForm({ ...form, full_name: event.target.value })}/></label>
        <label>Email<input required type="email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })}/></label>
        <label>Initial password<input required type="password" minLength="12" maxLength="128" autoComplete="new-password" value={form.initial_password} onChange={event => setForm({ ...form, initial_password: event.target.value })}/></label>
        <label>Department ID (optional)<input value={form.department_id} onChange={event => setForm({ ...form, department_id: event.target.value })} placeholder="Paste department UUID"/></label>
        {roleCodes.includes('patient') && <label>Linked patient ID<input required value={form.patient_id} onChange={event => setForm({ ...form, patient_id: event.target.value })} placeholder="Paste existing patient UUID"/></label>}
      </div>
      <div className="role-picker"><strong>Assign role(s)</strong><div>{availableRoles.map(([code, label]) => <label key={code}><input type="checkbox" checked={roleCodes.includes(code)} onChange={event => toggleRole(code, event.target.checked)}/><span>{label}</span></label>)}</div></div>
      <p className="security-warning">The initial password is sent to Supabase Auth and is not stored by NexusCare. Deliver it securely and arrange a password change; this build does not force a reset on first login. This endpoint requires the server-only SUPABASE_SECRET_KEY in backend/.env.</p>
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="primary-button" type="submit" disabled={create.isPending}>{create.isPending ? 'Creating account…' : 'Create account'}</button>
    </form>
    <div className="section-heading"><h2>Staff profiles</h2><span>{rows.length} PROFILE{rows.length === 1 ? '' : 'S'}</span></div>
    {staff.isPending ? <div className="empty-state">Loading staff profiles…</div>
      : staff.isError ? <div className="error-panel"><strong>Could not load staff</strong><p>{staff.error.message}</p></div>
      : rows.length === 0 ? <div className="empty-state"><Users size={24}/><strong>No profiles found</strong><span>Create the first administrator manually as documented in docs/setup.md.</span></div>
      : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Name</th><th>Email</th><th>Roles</th><th>Status</th></tr></thead><tbody>{rows.map(row => <tr key={row.profile_id}><td><strong>{row.full_name}</strong></td><td>{row.email}</td><td>{(row.roles || []).join(', ') || 'No roles'}</td><td>{row.is_active ? 'Active' : 'Inactive'}</td></tr>)}</tbody></table></div>}
  </section>
}
