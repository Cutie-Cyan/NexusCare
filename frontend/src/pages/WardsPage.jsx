import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { BedDouble, Plus, RefreshCw } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const blankWard = { code: '', name: '', ward_type: 'general', department_id: '' }
const blankBed = { ward_id: '', bed_number: '', notes: '' }

export function WardsPage({ roles = [] }) {
  const isAdmin = roles.includes('administrator')
  const [wardForm, setWardForm] = useState(blankWard)
  const [bedForm, setBedForm] = useState(blankBed)
  const [showWardForm, setShowWardForm] = useState(false)
  const [showBedForm, setShowBedForm] = useState(false)
  const [error, setError] = useState('')
  const client = useQueryClient()
  const wards = useQuery({ queryKey: ['ward-overview'], queryFn: () => apiRequest('/ward-overview') })
  const departments = useQuery({ queryKey: ['departments'], queryFn: () => apiRequest('/departments') })
  const createWard = useMutation({
    mutationFn: () => apiRequest('/wards', { method: 'POST', body: { ...wardForm, department_id: wardForm.department_id || null } }),
    onSuccess: () => { setWardForm(blankWard); setShowWardForm(false); setError(''); client.invalidateQueries({ queryKey: ['ward-overview'] }); client.invalidateQueries({ queryKey: ['wards'] }) },
    onError: err => setError(err.message),
  })
  const createBed = useMutation({
    mutationFn: () => apiRequest('/beds', { method: 'POST', body: { ...bedForm, notes: bedForm.notes || null } }),
    onSuccess: () => { setBedForm(blankBed); setShowBedForm(false); setError(''); client.invalidateQueries({ queryKey: ['ward-overview'] }); client.invalidateQueries({ queryKey: ['beds'] }) },
    onError: err => setError(err.message),
  })
  const wardRows = wards.data || []
  const departmentById = Object.fromEntries((departments.data || []).map(row => [row.id, row.name]))
  const bedTotal = wardRows.reduce((sum, row) => sum + (row.total_beds || 0), 0)
  const bedAvailable = wardRows.reduce((sum, row) => sum + (row.available_beds || 0), 0)
  const bedOccupied = wardRows.reduce((sum, row) => sum + (row.occupied_beds || 0), 0)
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">PATIENT MANAGEMENT</div><h1>Wards & Beds</h1><p className="page-description">Monitor occupancy and availability across active wards. Bed assignments are validated by the admissions API.</p></div><button className="icon-button" aria-label="Refresh ward occupancy" onClick={() => wards.refetch()} disabled={wards.isFetching}><RefreshCw size={16}/></button></div>
    <div className="metric-grid"><article className="metric-card"><span>Active wards</span><strong>{wardRows.length}</strong></article><article className="metric-card"><span>Total beds</span><strong>{bedTotal}</strong></article><article className="metric-card"><span>Available beds</span><strong>{bedAvailable}</strong></article><article className="metric-card"><span>Occupied beds</span><strong>{bedOccupied}</strong></article></div>
    {isAdmin && <div className="page-actions"><button className="primary-button" onClick={() => { setShowWardForm(v => !v); setShowBedForm(false); setError('') }}><Plus size={15}/> Add ward</button><button className="secondary-button" onClick={() => { setShowBedForm(v => !v); setShowWardForm(false); setError('') }}><BedDouble size={15}/> Add bed</button></div>}
    {showWardForm && <form className="data-form" onSubmit={e => { e.preventDefault(); setError(''); createWard.mutate() }}><h2>Create ward</h2><div className="form-grid">
      <label>Code<input required value={wardForm.code} onChange={e => setWardForm({ ...wardForm, code: e.target.value })} placeholder="WARD-03"/></label>
      <label>Ward name<input required value={wardForm.name} onChange={e => setWardForm({ ...wardForm, name: e.target.value })} placeholder="Pediatric Ward"/></label>
      <label>Type<select value={wardForm.ward_type} onChange={e => setWardForm({ ...wardForm, ward_type: e.target.value })}><option value="general">General</option><option value="emergency">Emergency</option><option value="maternity">Maternity</option><option value="pediatric">Pediatric</option><option value="intensive_care">Intensive care</option><option value="surgical">Surgical</option><option value="other">Other</option></select></label>
      <label>Department<select value={wardForm.department_id} onChange={e => setWardForm({ ...wardForm, department_id: e.target.value })}><option value="">No department assigned</option>{(departments.data || []).map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
    </div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" disabled={createWard.isPending}>{createWard.isPending ? 'Saving…' : 'Save ward'}</button></form>}
    {showBedForm && <form className="data-form" onSubmit={e => { e.preventDefault(); setError(''); createBed.mutate() }}><h2>Add bed</h2><div className="form-grid">
      <label>Ward<select required value={bedForm.ward_id} onChange={e => setBedForm({ ...bedForm, ward_id: e.target.value })}><option value="">Choose ward</option>{wardRows.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}</select></label>
      <label>Bed number<input required value={bedForm.bed_number} onChange={e => setBedForm({ ...bedForm, bed_number: e.target.value })} placeholder="G-011"/></label>
      <label>Notes<input value={bedForm.notes} onChange={e => setBedForm({ ...bedForm, notes: e.target.value })} placeholder="Optional"/></label>
    </div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" disabled={createBed.isPending}>{createBed.isPending ? 'Saving…' : 'Save bed'}</button></form>}
    {error && !showWardForm && !showBedForm && <p className="form-error" role="alert">{error}</p>}
    {wards.isPending ? <div className="empty-state">Loading ward occupancy…</div> : wards.isError ? <div className="error-panel"><strong>Could not load ward occupancy</strong><p>{wards.error.message}</p></div> : wardRows.length === 0 ? <div className="empty-state">No active wards found.</div> : <div className="ward-grid">{wardRows.map(ward => <article className="ward-card" key={ward.id}><div className="ward-card-heading"><div><span className="eyebrow">{ward.code}</span><h2>{ward.name}</h2><p>{departmentById[ward.department_id] || 'No department'} · {ward.ward_type}</p></div><BedDouble size={20}/></div><div className="ward-occupancy"><span>{ward.occupied_beds} occupied</span><span>{ward.available_beds} available</span></div><div className="occupancy-track"><span style={{ width: (ward.total_beds ? ward.occupied_beds / ward.total_beds * 100 : 0) + '%' }}/></div><div className="bed-grid">{(ward.beds || []).map(bed => <div className={'bed-chip bed-' + bed.status} key={bed.id} title={bed.bed_number + ': ' + bed.status}><span>{bed.bed_number}</span><small>{bed.status.replaceAll('_', ' ')}</small></div>)}</div></article>)}</div>}
    <p className="disclaimer">Bed status changes through admissions, transfers, and discharge workflows. This screen does not allow manual changes to occupied beds.</p>
  </section>
}
