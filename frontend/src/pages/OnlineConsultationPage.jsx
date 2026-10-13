import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Video } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

export function OnlineConsultationPage({ roles = [] }) {
  const canManage = roles.some(role => ['administrator', 'doctor', 'nurse'].includes(role))
  const [selectedId, setSelectedId] = useState('')
  const [form, setForm] = useState({ status: 'scheduled', meeting_url: '' })
  const [error, setError] = useState('')
  const client = useQueryClient()
  const consultations = useQuery({ queryKey: ['online-consultations'], queryFn: () => apiRequest('/online-consultations?limit=100') })
  const update = useMutation({
    mutationFn: () => apiRequest('/online-consultations/' + selectedId, { method: 'PATCH', body: { status: form.status, meeting_url: form.meeting_url || null } }),
    onSuccess: () => { setError(''); client.invalidateQueries({ queryKey: ['online-consultations'] }) },
    onError: err => setError(err.message),
  })
  const rows = consultations.data || []
  const selected = rows.find(row => row.id === selectedId)
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">HOSPITAL OPERATIONS</div><h1>Online Consultation</h1><p className="page-description">Review online consultation requests, schedule sessions, and maintain meeting links and session status.</p></div><span className="phase-tag">Authenticated</span></div>
    {consultations.isPending ? <div className="empty-state">Loading online consultations…</div> : consultations.isError ? <div className="error-panel"><strong>Online consultations unavailable</strong><p>{consultations.error.message}</p></div> : rows.length === 0 ? <div className="empty-state"><Video size={22}/>No online consultation requests found. Patients can request one from their appointment list.</div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Consultation</th><th>Appointment</th><th>Status</th><th>Meeting link</th><th>Started</th><th>Action</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><strong>{row.id}</strong></td><td>{row.appointment_id}</td><td>{row.status}</td><td>{row.meeting_url ? <a href={row.meeting_url} target="_blank" rel="noreferrer">Open link</a> : 'Not set'}</td><td>{row.started_at ? new Date(row.started_at).toLocaleString() : '—'}</td><td>{canManage && !['completed', 'cancelled'].includes(row.status) && <button className="table-action" onClick={() => { setSelectedId(row.id); setForm({ status: row.status, meeting_url: row.meeting_url || '' }); setError('') }}>Manage</button>}{!canManage && row.status === 'requested' && <button className="table-action" onClick={() => { setSelectedId(row.id); setForm({ status: 'cancelled', meeting_url: '' }) }}>Cancel request</button>}</td></tr>)}</tbody></table></div>}
    {selected && canManage && <section className="data-form receive-panel"><h2>Manage session</h2><form onSubmit={event => { event.preventDefault(); setError(''); update.mutate() }}><div className="form-grid"><label>Status<select value={form.status} onChange={event => setForm({ ...form, status: event.target.value })}><option value="requested">Requested</option><option value="scheduled">Scheduled</option><option value="in_progress">In progress</option><option value="completed">Completed</option><option value="cancelled">Cancelled</option></select></label><label>Meeting URL<input type="url" maxLength="2000" value={form.meeting_url} onChange={event => setForm({ ...form, meeting_url: event.target.value })} placeholder="https://…"/></label></div>{error && <p className="form-error" role="alert">{error}</p>}<div className="row-actions"><button className="primary-button" type="submit" disabled={update.isPending}>{update.isPending ? 'Saving…' : 'Save session'}</button><button className="secondary-button" type="button" onClick={() => setSelectedId('')}>Close</button></div></form></section>}
    {selected && !canManage && <section className="data-form receive-panel"><h2>Cancel request</h2><p>Are you sure you want to cancel this online consultation request?</p><button className="primary-button" onClick={() => update.mutate()} disabled={update.isPending}>{update.isPending ? 'Cancelling…' : 'Confirm cancellation'}</button><button className="secondary-button" onClick={() => setSelectedId('')}>Keep request</button>{error && <p className="form-error">{error}</p>}</section>}
    <div className="disclaimer">Only share meeting URLs with authorized participants. Do not place patient names or medical information in public meeting links.</div>
  </section>
}
