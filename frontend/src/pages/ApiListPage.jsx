import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, Search } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

function displayValue(value) {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'object') return JSON.stringify(value)
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(value)) {
    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
  }
  return String(value)
}

export function ApiListPage({ title, description, endpoint }) {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(0)
  const query = useQuery({
    queryKey: ['module-data', endpoint],
    queryFn: () => apiRequest(endpoint),
    refetchInterval: 30000,
  })
  const data = query.data
  const rows = Array.isArray(data) ? data : null
  const filtered = useMemo(() => {
    if (!rows) return []
    const term = search.trim().toLowerCase()
    return term ? rows.filter(row => JSON.stringify(row).toLowerCase().includes(term)) : rows
  }, [rows, search])
  const pageSize = 20
  const pageCount = Math.max(1, Math.ceil(filtered.length / pageSize))
  const currentRows = filtered.slice(page * pageSize, (page + 1) * pageSize)
  const columns = currentRows.length ? Object.keys(currentRows[0]) : []

  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">NEXUSCARE WORKSPACE</div><h1>{title}</h1><p className="page-description">{description}</p></div><button className="icon-button" aria-label="Refresh module data" title="Refresh data" onClick={() => query.refetch()} disabled={query.isFetching}><RefreshCw size={16}/></button></div>
    {query.isPending ? <div className="empty-state">Loading {title.toLowerCase()}…</div>
      : query.isError ? <div className="error-panel"><strong>Could not load {title.toLowerCase()}</strong><p>{query.error.message}</p><p>Check your role assignment, API permissions, and backend connection.</p></div>
      : rows ? <>
        <div className="table-toolbar"><div className="search-field"><Search size={16}/><input aria-label={'Search ' + title} value={search} onChange={event => { setSearch(event.target.value); setPage(0) }} placeholder={'Search ' + title.toLowerCase()}/></div><span>{filtered.length} record{filtered.length === 1 ? '' : 's'}</span></div>
        {filtered.length === 0 ? <div className="empty-state">No records found.</div> : <div className="data-table-wrap"><table className="data-table"><thead><tr>{columns.map(key => <th key={key}>{key.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{currentRows.map((row, index) => <tr key={row.id || row.profile_id || row.request_number || row.receipt_number || index}>{columns.map(key => <td key={key}>{displayValue(row[key])}</td>)}</tr>)}</tbody></table></div>}
        <div className="table-pagination"><span>Page {Math.min(page + 1, pageCount)} of {pageCount}</span><div><button className="secondary-button" disabled={page <= 0} onClick={() => setPage(value => Math.max(0, value - 1))}>Previous</button><button className="secondary-button" disabled={page + 1 >= pageCount} onClick={() => setPage(value => Math.min(pageCount - 1, value + 1))}>Next</button></div></div>
      </> : <div className="metric-grid">{Object.entries(data || {}).map(([key, value]) => <article className="metric-card" key={key}><span>{key.replaceAll('_', ' ')}</span><strong className="metric-value-small">{displayValue(value)}</strong></article>)}</div>}
  </section>
}
