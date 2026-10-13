import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Save, Search, Settings2 } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const display = value => value === null || value === undefined || value === '' ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value)
const dateLabel = value => value ? new Date(value).toLocaleString() : '—'

export function AdminOperationsPage({ mode, title, description }) {
  const [action, setAction] = useState('')
  const [resourceType, setResourceType] = useState('')
  const [selectedKey, setSelectedKey] = useState('')
  const [valueText, setValueText] = useState('{}')
  const [settingDescription, setSettingDescription] = useState('')
  const [error, setError] = useState('')
  const client = useQueryClient()
  const queryPath = mode === 'audit-logs'
    ? '/admin/audit-logs?limit=100' + (action ? '&action=' + encodeURIComponent(action) : '') + (resourceType ? '&resource_type=' + encodeURIComponent(resourceType) : '')
    : mode === 'departments' ? '/departments'
    : mode === 'settings' ? '/system-settings'
    : '/reports/summary'
  const query = useQuery({ queryKey: ['admin-operations', mode, action, resourceType], queryFn: () => apiRequest(queryPath), refetchInterval: mode === 'reports' ? 30000 : false })
  const saveSetting = useMutation({
    mutationFn: () => {
      let settingValue
      try { settingValue = JSON.parse(valueText) } catch { throw new Error('Setting value must be valid JSON.') }
      if (!settingValue || Array.isArray(settingValue) || typeof settingValue !== 'object') throw new Error('Setting value must be a JSON object.')
      return apiRequest('/system-settings/' + encodeURIComponent(selectedKey), { method: 'PUT', body: { setting_value: settingValue, description: settingDescription || null } })
    },
    onSuccess: () => { setError(''); client.invalidateQueries({ queryKey: ['admin-operations', 'settings'] }) },
    onError: err => setError(err.message),
  })
  const rows = Array.isArray(query.data) ? query.data : []
  function editSetting(row) {
    setSelectedKey(row.setting_key)
    setValueText(JSON.stringify(row.setting_value || {}, null, 2))
    setSettingDescription(row.description || '')
    setError('')
  }

  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">ADMINISTRATION</div><h1>{title}</h1><p className="page-description">{description}</p></div><button className="icon-button" aria-label="Refresh data" onClick={() => query.refetch()} disabled={query.isFetching}><RefreshCw size={16}/></button></div>
    {mode === 'audit-logs' && <div className="data-form"><h2><Search size={16}/> Filter audit events</h2><div className="form-grid"><label>Action<input value={action} onChange={event => setAction(event.target.value)} placeholder="e.g. patient.created"/></label><label>Resource type<input value={resourceType} onChange={event => setResourceType(event.target.value)} placeholder="e.g. patient, bill"/></label></div></div>}
    {mode === 'settings' && <div className="data-form"><h2><Settings2 size={16}/> Edit system setting</h2><div className="form-grid"><label>Setting key<select value={selectedKey} onChange={event => { const row = rows.find(item => item.setting_key === event.target.value); if (row) editSetting(row); else setSelectedKey(event.target.value) }}><option value="">Choose existing setting</option>{rows.map(row => <option key={row.id} value={row.setting_key}>{row.setting_key}</option>)}</select></label><label>Description<input value={settingDescription} onChange={event => setSettingDescription(event.target.value)} placeholder="Optional setting description"/></label><label className="form-grid-full">Setting value (JSON object)<textarea rows="7" spellCheck="false" value={valueText} onChange={event => setValueText(event.target.value)}/></label></div>{error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" disabled={!selectedKey || saveSetting.isPending} onClick={() => saveSetting.mutate()}><Save size={15}/>{saveSetting.isPending ? 'Saving…' : 'Save setting'}</button><p className="disclaimer">Only administrators can change settings. Store configuration only; never put passwords, access tokens, or secrets in system settings.</p></div>}
    {query.isPending ? <div className="empty-state">Loading {title.toLowerCase()}…</div>
      : query.isError ? <div className="error-panel"><strong>Could not load {title.toLowerCase()}</strong><p>{query.error.message}</p></div>
      : mode === 'reports' && query.data && typeof query.data === 'object' ? <div className="metric-grid">{Object.entries(query.data).map(([key, value]) => <article className="metric-card" key={key}><span>{key.replaceAll('_', ' ')}</span><strong className="metric-value-small">{display(value)}</strong></article>)}</div>
      : mode === 'settings' ? rows.length ? <div className="data-table-wrap"><table className="data-table"><thead><tr><th>Setting key</th><th>Description</th><th>Updated</th><th>Action</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><td><strong>{row.setting_key}</strong></td><td>{row.description || '—'}</td><td>{dateLabel(row.updated_at)}</td><td><button className="table-action" onClick={() => editSetting(row)}>Edit</button></td></tr>)}</tbody></table></div> : <div className="empty-state">No settings exist yet. Create the first key in the settings form by typing its key is not currently supported; seed a setting through the administrator API first.</div>
      : rows.length ? <div className="data-table-wrap"><table className="data-table"><thead><tr>{Object.keys(rows[0]).map(key => <th key={key}>{key.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{rows.map((row, index) => <tr key={row.id || index}>{Object.keys(rows[0]).map(key => <td key={key}>{mode === 'audit-logs' && key === 'created_at' ? dateLabel(row[key]) : display(row[key])}</td>)}</tr>)}</tbody></table></div>
      : <div className="empty-state">No records to display.</div>}
    {mode === 'reports' && <p className="disclaimer">Summary metrics refresh every 30 seconds. Metrics are operational indicators, not clinical advice.</p>}
  </section>
}
