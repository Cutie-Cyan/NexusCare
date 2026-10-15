import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import {
  Activity, BedDouble, Building2, CalendarDays, ChartNoAxesCombined, FileCheck2,
  ChevronRight, ClipboardList, CreditCard, FlaskConical, HeartPulse,
  LayoutDashboard, LogOut, Package, Pill, ReceiptText, ScrollText, Settings,
  ShieldCheck, Siren, Stethoscope, UserPlus, UserRound, Users, Video, Wallet, X,
} from 'lucide-react'
import { canAccessPath } from '../../permissions.js'

const groups = [
  { label: 'OVERVIEW', items: [['Dashboard', '/', LayoutDashboard], ['Ward Whiteboard', '/whiteboard', Activity]] },
  { label: 'PATIENT MANAGEMENT', items: [
    ['Patients', '/patients', Users], ['Registration', '/registration', UserPlus],
    ['Admissions', '/admissions', ClipboardList], ['Emergency Room', '/emergency', Siren],
    ['Wards & Beds', '/wards', BedDouble],
  ]},
  { label: 'CLINICAL SERVICES', items: [
    ['Consultations', '/consultations', Stethoscope], ['Nursing Station', '/nursing', Activity],
    ['Laboratory', '/laboratory', FlaskConical], ['Prescriptions', '/prescriptions', ClipboardList],
  ]},
  { label: 'HOSPITAL OPERATIONS', items: [
    ['Pharmacy', '/pharmacy', Pill], ['Inventory', '/inventory', Package],
    ['Procurement', '/procurement', ClipboardList], ['Appointments', '/appointments', CalendarDays],
    ['Online Consultation', '/online-consultation', Video],
  ]},
  { label: 'FINANCIAL MANAGEMENT', items: [
    ['Billing', '/billing', Wallet], ['Payments', '/payments', CreditCard], ['Receipts', '/receipts', ReceiptText],
    ['Discounts & Benefits', '/financial-assistance', FileCheck2],
  ]},
  { label: 'ADMINISTRATION', items: [
    ['Staff & Accounts', '/staff', ShieldCheck], ['Departments', '/departments', Building2],
    ['Service Fees', '/service-fees', CreditCard], ['Reports & Analytics', '/reports', ChartNoAxesCombined],
    ['Audit Logs', '/audit-logs', ScrollText], ['Settings', '/settings', Settings],
  ]},
]

export function Sidebar({ mobileOpen, onClose, userEmail, roles = [] }) {
  const [profileOpen, setProfileOpen] = useState(false)
  const visibleGroups = groups
    .map(group => ({ ...group, items: group.items.filter(([, path]) => canAccessPath(roles, path)) }))
    .filter(group => group.items.length > 0)

  return <aside className={'sidebar ' + (mobileOpen ? 'sidebar-mobile-open' : '')} aria-label="Main navigation">
    <div className="brand-row">
      <div className="brand-mark"><HeartPulse size={19}/></div>
      <div className="brand-copy"><strong>NexusCare</strong><span>HOSPITAL SYSTEM</span></div>
      <button className="sidebar-mobile-close" aria-label="Close navigation" onClick={onClose}><X size={18}/></button>
    </div>
    <div className="workspace-switcher"><div className="workspace-icon">N</div><div className="workspace-copy"><strong>NexusCare Hospital</strong></div><ChevronRight className="workspace-chevron" size={14}/></div>
    <nav className="sidebar-nav">{visibleGroups.map(group => <section className="nav-group" key={group.label} aria-label={group.label}>
      <div className="nav-group-label">{group.label}</div>
      {group.items.map(([label, path, Icon]) => <NavLink key={path} to={path} end={path === '/'} onClick={onClose} className={({ isActive }) => 'nav-link ' + (isActive ? 'nav-link-active' : '')} title={label} aria-label={label}>
        <Icon className="nav-icon" size={18}/><span className="nav-label">{label}</span>
      </NavLink>)}
    </section>)}</nav>
    <div className="sidebar-bottom">
      <button className={'profile-row ' + (profileOpen ? 'profile-row-open' : '')} onClick={() => setProfileOpen(value => !value)} aria-expanded={profileOpen}>
        <div className="profile-avatar"><UserRound size={16}/></div><div className="profile-copy"><strong>{userEmail ? userEmail.split('@')[0] : 'Signed in'}</strong><span>{roles.join(', ') || 'Supabase Auth'}</span></div><ChevronRight className="profile-chevron" size={14}/>
      </button>
      {profileOpen && <div className="profile-popover"><p>Signed in through Supabase Auth. API permissions are checked on the server.</p><button onClick={() => setProfileOpen(false)}><LogOut size={14}/> Close menu</button></div>}
    </div>
  </aside>
}
