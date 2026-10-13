import { useQuery } from '@tanstack/react-query'
import { Activity, BedDouble, CalendarDays, ClipboardList, Package, Wallet } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const metrics = [
  ['active_patients', 'Active patients', Activity],
  ['active_admissions', 'Active admissions', BedDouble],
  ['upcoming_or_active_appointments', 'Appointments', CalendarDays],
  ['posted_payments_total', 'Posted payments', Wallet],
  ['open_bills', 'Open bills', ClipboardList],
  ['low_stock_items', 'Low-stock items', Package],
]

export function DashboardPage() {
  const summary = useQuery({ queryKey: ['reports-summary'], queryFn: () => apiRequest('/reports/summary') })
  return <section className="page-wrap"><div className="page-heading"><div><div className="eyebrow">NEXUSCARE WORKSPACE</div><h1>Dashboard</h1><p className="page-description">Operational summary from the authenticated NexusCare API.</p></div><span className="phase-tag">Live API</span></div>
    {summary.isPending ? <div className="empty-state">Loading dashboard summary…</div>
      : summary.isError ? <div className="error-panel"><strong>Dashboard data unavailable</strong><p>{summary.error.message}</p><p>The reporting endpoint is restricted to administrator, information officer, and cashier roles.</p></div>
      : <div className="metric-grid">{metrics.map(([key, label, Icon]) => <article className="metric-card" key={key}><div className="metric-icon"><Icon size={18}/></div><span>{label}</span><strong>{key === 'posted_payments_total' ? new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' }).format(Number(summary.data[key] || 0)) : Number(summary.data[key] || 0).toLocaleString()}</strong></article>)}</div>}
    <div className="disclaimer">Development environment · Use fictional demo data only. Dashboard values reflect the current API response, not independently audited financial reporting.</div>
  </section>
}
