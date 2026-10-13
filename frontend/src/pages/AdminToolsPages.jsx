import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { FileSearch, Printer, RefreshCw, Save, Settings2, ChartNoAxesCombined } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

function pretty(value) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

export function ReceiptsPage() {
  const [search, setSearch] = useState('')
  const receipts = useQuery({ queryKey: ['receipts'], queryFn: () => apiRequest('/receipts?limit=100') })
  const rows = receipts.data || []
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return q ? rows.filter(row => JSON.stringify(row).toLowerCase().includes(q)) : rows
  }, [rows, search])
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">FINANCIAL MANAGEMENT</div><h1>Receipts</h1><p className="page-description">Review receipts created by successful payment postings. Receipt records are immutable.</p></div><button className="icon-button" aria-label="Refresh receipts" onClick={() => receipts.refetch()} disabled={receipts.isFetching}><RefreshCw size={16}/></button></div>
    <div className="table-toolbar"><div className="search-field"><FileSearch size={16}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search receipt, bill, or payment"/></div><span>{filtered.length} receipt{filtered.length === 1 ? '' : 's'}</span></div>
    {receipts.isPending ? <div className="empty-state">Loading receipts…</div> : receipts.isError ? <div className="error-panel"><strong>Receipts unavailable</strong><p>{receipts.error.message}</p></div> : filtered.length === 0 ? <div className="empty-state">No receipts match this search.</div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Receipt</th><th>Issued</th><th>Bill</th><th>Payment method</th><th>Amount</th><th>Status</th><th>Action</th></tr></thead><tbody>{filtered.map(row => <tr key={row.receipt_number}><td><strong>{row.receipt_number}</strong></td><td>{row.issued_at ? new Date(row.issued_at).toLocaleString() : '—'}</td><td>{row.bill_number}</td><td>{row.payment_method}</td><td>₱{Number(row.payment_amount).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td><td>{row.payment_status}</td><td><button className="table-action" onClick={() => window.print()}><Printer size={13}/> Print list</button></td></tr>)}</tbody></table></div>}
    <p className="disclaimer">For a single receipt, use its receipt number with GET /api/v1/receipts/{'{receipt_number}'}. Printing this view prints the current page.</p>
  </section>
}

export function ReportsPage() {
  const reports = useQuery({ queryKey: ['reports-summary'], queryFn: () => apiRequest('/reports/summary'), refetchInterval: 60000 })
  const labels = {
    active_patients: ['Active patients', 'Unique active patient records'],
    active_admissions: ['Active admissions', 'Patients currently admitted'],
    upcoming_or_active_appointments: ['Appointments', 'Scheduled, confirmed, or checked in'],
    posted_payments_total: ['Posted payments', 'Sum of payments not reversed'],
    open_bills: ['Open bills', 'Bills with outstanding balances'],
    low_stock_items: ['Low-stock items', 'Inventory at or below reorder level'],
  }
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">OPERATIONS</div><h1>Reports & Analytics</h1><p className="page-description">Operational summary based on current authorized database records.</p></div><button className="icon-button" aria-label="Refresh reports" onClick={() => reports.refetch()} disabled={reports.isFetching}><RefreshCw size={16}/></button></div>
    {reports.isPending ? <div className="empty-state">Preparing reports…</div> : reports.isError ? <div className="error-panel"><strong>Reports unavailable</strong><p>{reports.error.message}</p></div> : <div className="metric-grid">{Object.entries(reports.data || {}).map(([key, value]) => <article className="metric-card" key={key}><span>{labels[key]?.[0] || key.replaceAll('_', ' ')}</span><strong className="metric-value-small">{key === 'posted_payments_total' ? '₱' + Number(value).toLocaleString('en-PH', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : Number(value).toLocaleString()}</strong><small>{labels[key]?.[1] || ''}</small></article>)}</div>}
    <p className="disclaimer">Summary counts are not a substitute for audited financial statements or clinical-quality reporting. Access is enforced by the backend.</p>
  </section>
}

export function AuditLogsPage() {
  const [action, setAction] = useState('')
  const [resourceType, setResourceType] = useState('')
  const [submitted, setSubmitted] = useState({ action: '', resourceType: '' })
  const query = useQuery({
    queryKey: ['audit-logs', submitted],
    queryFn: () => {
      const params = new URLSearchParams({ limit: '100' })
      if (submitted.action) params.set('action', submitted.action)
      if (submitted.resourceType) params.set('resource_type', submitted.resourceType)
      return apiRequest('/admin/audit-logs?' + params.toString())
    },
  })
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">ADMINISTRATION</div><h1>Audit Logs</h1><p className="page-description">Search the append-only activity trail. Only administrators can access this screen.</p></div><button className="icon-button" aria-label="Refresh audit logs" onClick={() => query.refetch()} disabled={query.isFetching}><RefreshCw size={16}/></button></div>
    <form className="data-form" onSubmit={e => { e.preventDefault(); setSubmitted({ action: action.trim(), resourceType: resourceType.trim() }) }}><div className="form-grid"><label>Exact action<input value={action} onChange={e => setAction(e.target.value)} placeholder="payment.posted"/></label><label>Resource type<input value={resourceType} onChange={e => setResourceType(e.target.value)} placeholder="payment"/></label></div><button className="primary-button" type="submit"><FileSearch size={15}/> Apply filters</button></form>
    {query.isPending ? <div className="empty-state">Loading audit trail…</div> : query.isError ? <div className="error-panel"><strong>Audit logs unavailable</strong><p>{query.error.message}</p></div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Time</th><th>Action</th><th>Resource</th><th>Resource ID</th><th>Actor profile</th><th>Details</th></tr></thead><tbody>{(query.data || []).map(row => <tr key={row.id}><td>{row.created_at ? new Date(row.created_at).toLocaleString() : '—'}</td><td><strong>{row.action}</strong></td><td>{row.resource_type}</td><td>{row.resource_id || '—'}</td><td>{row.actor_profile_id || '—'}</td><td><pre className="audit-json">{pretty(row.details)}</pre></td></tr>)}</tbody></table>{(query.data || []).length === 0 && <div className="empty-state">No audit events match these filters.</div>}</div>}
    <p className="disclaimer">Audit data is read-only. Sensitive clinical values should not be placed in audit details; this view may contain identifiers and must be used only for authorized administrative review.</p>
  </section>
}

export function SettingsPage() {
  const [settingKey, setSettingKey] = useState('')
  const [settingValue, setSettingValue] = useState('{\\n  \\n}')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const client = useQueryClient()
  const settings = useQuery({ queryKey: ['system-settings'], queryFn: () => apiRequest('/system-settings') })
  const save = useMutation({
    mutationFn: () => {
      let parsed
      try { parsed = JSON.parse(settingValue) } catch { throw new Error('Setting value must be valid JSON.') }
      if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error('Setting value must be a JSON object.')
      return apiRequest('/system-settings/' + encodeURIComponent(settingKey.trim()), { method: 'PUT', body: { setting_value: parsed, description: description || null } })
    },
    onSuccess: () => { setError(''); client.invalidateQueries({ queryKey: ['system-settings'] }) },
    onError: err => setError(err.message),
  })
  const rows = settings.data || []
  function edit(row) {
    setSettingKey(row.setting_key)
    setSettingValue(JSON.stringify(row.setting_value, null, 2))
    setDescription(row.description || '')
    setError('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">ADMINISTRATION</div><h1>System Settings</h1><p className="page-description">Manage structured configuration values. Only administrators can view or update settings.</p></div><button className="icon-button" aria-label="Refresh settings" onClick={() => settings.refetch()} disabled={settings.isFetching}><RefreshCw size={16}/></button></div>
    <form className="data-form" onSubmit={e => { e.preventDefault(); setError(''); save.mutate() }}><h2><Settings2 size={16}/> Save setting</h2><div className="form-grid"><label>Setting key<input required maxLength="120" value={settingKey} onChange={e => setSettingKey(e.target.value)} placeholder="hospital.profile"/></label><label>Description<input value={description} onChange={e => setDescription(e.target.value)} placeholder="Purpose of this setting"/></label></div><label>Value (JSON object)<textarea required rows={5} value={settingValue} onChange={e => setSettingValue(e.target.value)} spellCheck={false}/></label>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" disabled={save.isPending}><Save size={15}/>{save.isPending ? 'Saving…' : 'Save setting'}</button></form>
    {settings.isPending ? <div className="empty-state">Loading settings…</div> : settings.isError ? <div className="error-panel"><strong>Settings unavailable</strong><p>{settings.error.message}</p></div> : rows.length === 0 ? <div className="empty-state">No settings saved yet.</div> : <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Key</th><th>Description</th><th>Value</th><th>Updated</th><th/></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><strong>{row.setting_key}</strong></td><td>{row.description || '—'}</td><td><pre className="audit-json">{pretty(row.setting_value)}</pre></td><td>{row.updated_at ? new Date(row.updated_at).toLocaleString() : '—'}</td><td><button className="table-action" onClick={() => edit(row)}><Save size={13}/> Edit</button></td></tr>)}</tbody></table></div>}
    <p className="disclaimer">Store configuration only; do not put API keys, passwords, tokens, or other secrets in settings.</p>
  </section>
}
