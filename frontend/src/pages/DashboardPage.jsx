import { useQuery } from '@tanstack/react-query'
import { Activity, BedDouble, CalendarDays, ClipboardList, Package, Wallet, Siren, FlaskConical, CheckCircle2 } from 'lucide-react'
import { apiRequest } from '../lib/api.js'

const financialMetrics = [
  ['active_patients', 'Active patients', Activity],
  ['active_admissions', 'Active admissions', BedDouble],
  ['upcoming_or_active_appointments', 'Appointments', CalendarDays],
  ['posted_payments_total', 'Posted payments', Wallet],
  ['open_bills', 'Open bills', ClipboardList],
  ['low_stock_items', 'Low-stock items', Package],
]
const operationsMetrics = [
  ['active_admissions', 'Active admissions', BedDouble],
  ['occupied_beds', 'Occupied beds', BedDouble],
  ['available_beds', 'Available beds', CheckCircle2],
  ['emergency_queue', 'Emergency queue', Siren],
  ['pending_laboratory_orders', 'Pending lab orders', FlaskConical],
  ['low_stock_items', 'Low-stock items', Package],
  ['active_appointments', 'Active appointments', CalendarDays],
]

export function DashboardPage({ roles = [] }) {
  const financeAccess = roles.some(role => ['administrator', 'information_officer', 'cashier'].includes(role))
  const patientAccess = roles.includes('patient') && !financeAccess
  const query = useQuery({
    queryKey: ['dashboard-data', financeAccess, patientAccess],
    queryFn: () => apiRequest(financeAccess ? '/reports/summary' : patientAccess ? '/appointments?limit=100' : '/whiteboard'),
    refetchInterval: 30000,
  })
  const data = query.data
  const metrics = financeAccess ? financialMetrics : operationsMetrics
  return <section className="page-wrap"><div className="page-heading"><div><div className="eyebrow">NEXUSCARE WORKSPACE</div><h1>Dashboard</h1><p className="page-description">Role-appropriate operational information from the authenticated NexusCare API.</p></div></div>
    {query.isPending ? <div className="empty-state">Loading dashboard summary…</div>
      : query.isError ? <div className="error-panel"><strong>Dashboard data unavailable</strong><p>{query.error.message}</p><p>Your account may not have permission to view this summary, or the backend may be unavailable.</p></div>
      : patientAccess ? <div className="metric-grid"><article className="metric-card"><div className="metric-icon"><CalendarDays size={18}/></div><span>Your appointments</span><strong>{(data || []).length}</strong></article></div>
      : <div className="metric-grid">{metrics.map(([key, label, Icon]) => <article className="metric-card" key={key}><div className="metric-icon"><Icon size={18}/></div><span>{label}</span><strong>{key === 'posted_payments_total' ? new Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' }).format(Number(data[key] || 0)) : Number(data[key] || 0).toLocaleString()}</strong></article>)}</div>}
  </section>
}
