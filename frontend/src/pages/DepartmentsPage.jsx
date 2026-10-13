import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, Plus, RefreshCw } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const empty = { code: '', name: '', description: '' }

export function DepartmentsPage({ roles = [] }) {
  const canManage = roles.includes('administrator')
  const [form, setForm] = useState(empty)
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState('')
  const client = useQueryClient()
  const departments = useQuery({ queryKey: ['departments'], queryFn: () => apiRequest('/departments') })
  const wards = useQuery({ queryKey: ['ward-overview'], queryFn: () => apiRequest('/ward-overview') })
  const create = useMutation({
    mutationFn: () => apiRequest('/departments', { method: 'POST', body: { ...form, description: form.description || null } }),
    onSuccess: () => { setForm(empty); setShowForm(false); setError(''); client.invalidateQueries({ queryKey: ['departments'] }) },
    onError: err => setError(err.message),
  })
  const rows = departments.data || []
  const wardCounts = Object.fromEntries(rows.map(d => [d.id, (wards.data || []).filter(w => w.department_id === d.id).length]))
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">ADMINISTRATION</div><h1>Departments</h1><p className="page-description">Manage departments used by wards, clinical encounters, and appointment scheduling.</p></div><button className="icon-button" aria-label="Refresh departments" onClick={() => departments.refetch()} disabled={departments.isFetching}><RefreshCw size={16}/></button></div>
    <div className="page-actions"><div className="metric-card"><span>Active departments</span><strong>{rows.length}</strong></div>{canManage && <button className="primary-button" onClick={() => { setShowForm(v => !v); setError('') }}><Plus size={15}/>{showForm ? 'Close form' : 'Add department'}</button>}</div>
    {showForm && <form className="data-form" onSubmit={e => { e.preventDefault(); setError(''); create.mutate() }}><h2><Building2 size={16}/> New department</h2><div className="form-grid">
      <label>Code<input required minLength="2" maxLength="40" value={form.code} onChange={e => setForm({ ...form, code: e.target.value.toUpperCase() })} placeholder="CARDIOLOGY"/></label>
      <label>Name<input required minLength="2" maxLength="120" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="Cardiology"/></label>
      <label>Description<input value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} placeholder="Optional"/></label>
    </div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" disabled={create.isPending}>{create.isPending ? 'Saving…' : 'Save department'}</button></form>}
    {departments.isPending ? <div className="empty-state">Loading departments…</div> : departments.isError ? <div className="error-panel"><strong>Could not load departments</strong><p>{departments.error.message}</p></div> : rows.length === 0 ? <div className="empty-state">No active departments found.</div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Department</th><th>Code</th><th>Description</th><th>Active wards</th><th>Status</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><strong>{row.name}</strong></td><td>{row.code}</td><td>{row.description || '—'}</td><td>{wardCounts[row.id] || 0}</td><td><span className="status-pill status-active">Active</span></td></tr>)}</tbody></table></div>}
    <p className="disclaimer">Only administrators can create departments. Existing department codes are unique and changes are recorded in the audit log.</p>
  </section>
}
