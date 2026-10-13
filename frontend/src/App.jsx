import { useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AppLayout } from './layouts/AppLayout.jsx'
import { AuthProvider, useAuth } from './AuthProvider.jsx'
import { DashboardPage } from './pages/DashboardPage.jsx'
import { LoginPage } from './pages/LoginPage.jsx'
import { PatientsPage } from './pages/PatientsPage.jsx'
import { PlaceholderPage } from './pages/PlaceholderPage.jsx'
import { apiRequest } from './lib/api.js'
import { canAccessPath } from './permissions.js'

const pages = [
  ['/registration', 'Registration', 'Patient registration and demographic updates are available through the patient API; a dedicated registration workflow is still being refined.'],
  ['/admissions', 'Admissions', 'Admission, transfer, discharge, ward, and bed APIs are available. Dedicated workflow screens remain in progress.'],
  ['/emergency', 'Emergency Room', 'Emergency registration and triage APIs are available for authorized clinical roles.'],
  ['/wards', 'Wards & Beds', 'Ward and bed availability APIs are available.'],
  ['/consultations', 'Consultations', 'Clinical encounters, diagnoses, consultations, and append-only notes are available through the API.'],
  ['/nursing', 'Nursing Station', 'Vital signs and nursing-note APIs are available for authorized nursing staff.'],
  ['/laboratory', 'Laboratory', 'Laboratory orders, payment eligibility, processing, results, and independent verification APIs are available.'],
  ['/prescriptions', 'Prescriptions', 'Doctor-issued prescriptions and prescription item APIs are available.'],
  ['/pharmacy', 'Pharmacy', 'Medicine catalog, batches, stock levels, dispensing, and automatic bill charges are available.'],
  ['/inventory', 'Inventory', 'Supplier records, stock movements, reorder checks, and transaction history APIs are available.'],
  ['/procurement', 'Procurement', 'Procurement requests, administrator approval, receiving records, and stock updates are available.'],
  ['/appointments', 'Appointments', 'Appointment scheduling, patient requests, cancellation, and clinician schedules are available.'],
  ['/online-consultation', 'Online Consultation', 'Online consultation requests and session lifecycle APIs are available.'],
  ['/billing', 'Billing', 'Itemized bills, service fees, automatic laboratory/pharmacy/professional-fee charges, and balance APIs are available.'],
  ['/payments', 'Payments', 'Idempotent payment posting and administrator-only audited payment reversals are available.'],
  ['/receipts', 'Receipts', 'Receipt records are created with successful payment postings and can be retrieved by receipt number.'],
  ['/staff', 'Staff & Accounts', 'Supabase Auth and role checks are active. Staff account provisioning still requires administrator setup and server-only credentials.'],
  ['/departments', 'Departments', 'Department records support ward, encounter, and appointment workflows. Department administration UI remains in progress.'],
  ['/service-fees', 'Service Fees', 'Administrator-only service-fee creation and updates are available through the API.'],
  ['/reports', 'Reports & Analytics', 'The reporting API exposes authorized operational summary metrics.'],
  ['/audit-logs', 'Audit Logs', 'Administrators can search the audit trail through the API.'],
  ['/settings', 'Settings', 'Administrator-only system-setting APIs are available.'],
]

function ProfileIncomplete({ onSignOut }) {
  return <main className="auth-page"><section className="auth-card"><h1>Account setup is incomplete</h1><p className="auth-description">You are authenticated, but your account does not have an active NexusCare profile and role assignment yet. Ask the administrator to finish account setup.</p><button className="primary-button" onClick={onSignOut}>Sign out</button></section></main>
}

function AuthenticatedWorkspace() {
  const { session, loading, configured, signOut } = useAuth()
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('nexuscare-theme') || 'dark' } catch { return 'dark' }
  })
  const identity = useQuery({
    queryKey: ['identity', session?.user?.id],
    queryFn: () => apiRequest('/auth/me'),
    enabled: Boolean(session),
    retry: false,
    staleTime: 60000,
  })
  function toggleTheme() {
    setTheme(current => {
      const next = current === 'dark' ? 'light' : 'dark'
      try { localStorage.setItem('nexuscare-theme', next) } catch {}
      return next
    })
  }
  async function handleSignOut() {
    try { await signOut() } catch (error) { window.alert(error.message || 'Unable to sign out.') }
  }
  if (loading) return <main className="auth-page"><div className="empty-state">Checking your session…</div></main>
  if (!configured || !session) return <LoginPage />
  if (identity.isPending) return <main className="auth-page"><div className="empty-state">Loading your NexusCare profile…</div></main>
  if (identity.isError) return <main className="auth-page"><section className="auth-card"><h1>Could not connect to NexusCare</h1><p className="auth-description">{identity.error.message}</p><p className="auth-description">Confirm FastAPI is running and VITE_API_BASE_URL points to its API base.</p><button className="primary-button" onClick={handleSignOut}>Sign out</button></section></main>
  if (!identity.data.profile_complete) return <ProfileIncomplete onSignOut={handleSignOut}/>
  const roles = identity.data.roles || []

  return <div className={'app-shell theme-' + theme}>
    <AppLayout theme={theme} onToggleTheme={toggleTheme} userEmail={session.user?.email} onSignOut={handleSignOut} roles={roles}>
      <Routes>
        <Route path="/" element={<DashboardPage roles={roles} />} />
        <Route path="/patients" element={canAccessPath(roles, '/patients') ? <PatientsPage /> : <Navigate to="/" replace />} />
        {pages.map(([path, title, description]) => <Route key={path} path={path} element={canAccessPath(roles, path) ? <PlaceholderPage title={title} description={description} /> : <Navigate to="/" replace />} />)}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  </div>
}

export default function App() {
  return <AuthProvider><AuthenticatedWorkspace /></AuthProvider>
}
