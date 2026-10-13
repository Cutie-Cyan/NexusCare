import { useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './layouts/AppLayout.jsx'
import { AuthProvider, useAuth } from './AuthProvider.jsx'
import { DashboardPage } from './pages/DashboardPage.jsx'
import { LoginPage } from './pages/LoginPage.jsx'
import { PatientsPage } from './pages/PatientsPage.jsx'
import { PlaceholderPage } from './pages/PlaceholderPage.jsx'

const pages = [
  ['/registration', 'Registration', 'Patient registration and demographic updates are available through the patient API; a dedicated registration workflow is still being refined.'],
  ['/admissions', 'Admissions', 'Admission, transfer, discharge, ward, and bed APIs are available. Dedicated workflow screens remain in progress.'],
  ['/emergency', 'Emergency Room', 'Emergency registration and triage APIs are available for authorized clinical roles.'],
  ['/wards', 'Wards & Beds', 'View ward and bed availability through the admissions API.'],
  ['/consultations', 'Consultations', 'Clinical encounters, diagnoses, consultations, and append-only notes are available through the API.'],
  ['/nursing', 'Nursing Station', 'Vital signs and nursing-note APIs are available for authorized nursing staff.'],
  ['/laboratory', 'Laboratory', 'Laboratory orders, processing status, results, and independent result verification APIs are available.'],
  ['/prescriptions', 'Prescriptions', 'Doctor-issued prescriptions and prescription item APIs are available.'],
  ['/pharmacy', 'Pharmacy', 'Medicine catalog, batches, stock levels, and safe prescription dispensing APIs are available.'],
  ['/inventory', 'Inventory', 'Supplier records, stock movements, reorder checks, and transaction history APIs are available.'],
  ['/appointments', 'Appointments', 'Appointment scheduling, status updates, and clinician scheduling APIs are available.'],
  ['/online-consultation', 'Online Consultation', 'Online-consultation session records can be created for eligible appointments.'],
  ['/billing', 'Billing', 'Itemized bills, service catalog, and bill balance APIs are available.'],
  ['/payments', 'Payments', 'Idempotent payment posting and administrator-only audited payment reversals are available.'],
  ['/receipts', 'Receipts', 'Receipt records are created with successful payment postings. Dedicated printable receipt UI remains in progress.'],
  ['/staff', 'Staff & Accounts', 'Supabase Auth and role checks are active. Administrative staff provisioning still requires a dedicated workflow.'],
  ['/departments', 'Departments', 'Department records support ward, encounter, and appointment workflows. Department administration UI remains in progress.'],
  ['/service-fees', 'Service Fees', 'The service catalog API provides active billable services and prices.'],
  ['/reports', 'Reports & Analytics', 'The reporting API exposes authorized operational summary metrics.'],
  ['/audit-logs', 'Audit Logs', 'Sensitive workflows write audit records. A dedicated audit-log browser is not yet exposed.'],
  ['/settings', 'Settings', 'Administrator-only system-setting APIs are available.'],
]

function AuthenticatedWorkspace() {
  const { session, loading, configured, signOut } = useAuth()
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('nexuscare-theme') || 'dark' } catch { return 'dark' }
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

  return <div className={'app-shell theme-' + theme}>
    <AppLayout theme={theme} onToggleTheme={toggleTheme} userEmail={session.user?.email} onSignOut={handleSignOut}>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/patients" element={<PatientsPage />} />
        {pages.map(([path, title, description]) => <Route key={path} path={path} element={<PlaceholderPage title={title} description={description} />} />)}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppLayout>
  </div>
}

export default function App() {
  return <AuthProvider><AuthenticatedWorkspace /></AuthProvider>
}
