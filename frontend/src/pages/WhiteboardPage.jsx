import { useQuery } from '@tanstack/react-query'
import { Activity, BedDouble, CalendarDays, ClipboardList, FlaskConical, Package, RefreshCw, Siren } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const metrics = [
  ['active_admissions', 'Active admissions', ClipboardList],
  ['occupied_beds', 'Occupied beds', BedDouble],
  ['available_beds', 'Available beds', BedDouble],
  ['emergency_queue', 'Emergency queue', Siren],
  ['pending_laboratory_orders', 'Pending lab orders', FlaskConical],
  ['low_stock_items', 'Low-stock items', Package],
  ['active_appointments', 'Active appointments', CalendarDays],
]
const labels = Object.fromEntries(metrics.map(([key, label]) => [key, label]))

export function WhiteboardPage() {
  const query = useQuery({ queryKey: ['whiteboard'], queryFn: () => apiRequest('/whiteboard'), refetchInterval: 15000 })
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">HOSPITAL OPERATIONS</div><h1>Ward Whiteboard</h1><p className="page-description">Privacy-conscious operational counts for authorized clinical and hospital staff. No patient names are displayed.</p></div><button className="icon-button" aria-label="Refresh whiteboard" onClick={() => query.refetch()} disabled={query.isFetching}><RefreshCw size={16}/></button></div>
    {query.isPending ? <div className="empty-state">Loading operational summary…</div>
      : query.isError ? <div className="error-panel"><strong>Whiteboard unavailable</strong><p>{query.error.message}</p></div>
      : <><div className="metric-grid">{metrics.map(([key, label, Icon]) => <article className="metric-card" key={key}><div className="metric-icon"><Icon size={17}/></div><span>{label}</span><strong>{Number(query.data?.[key] || 0).toLocaleString()}</strong></article>)}</div><p className="disclaimer">Updated {query.data?.generated_at ? new Date(query.data.generated_at).toLocaleString() : 'just now'}. The board refreshes every 15 seconds.</p></>}
  </section>
}
