import { useState } from 'react'
import { HeartPulse, ShieldCheck } from 'lucide-react'
import { useAuth } from '../AuthProvider.jsx'

export function LoginPage() {
  const { signIn, configured } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try { await signIn(email.trim(), password) }
    catch (err) { setError(err.message || 'Unable to sign in.') }
    finally { setSubmitting(false) }
  }
  return <main className="auth-page"><section className="auth-card">
    <div className="auth-brand"><span><HeartPulse size={24}/></span><div><strong>NexusCare</strong><small>HOSPITAL INFORMATION SYSTEM</small></div></div>
    <h1>Sign in to your workspace</h1>
    <p className="auth-description">Use your authorized NexusCare account. Access is checked again by the FastAPI backend.</p>
    {!configured ? <div className="auth-notice"><strong>Setup required</strong><p>Add these public frontend settings to <code>frontend/.env.local</code>, then restart Vite:</p><code>VITE_SUPABASE_URL=your-project-url</code><code>VITE_SUPABASE_PUBLISHABLE_KEY=your-publishable-key</code><p>Never place a Supabase secret/service-role key or database password in a variable starting with <code>VITE_</code>.</p></div> : <form className="auth-form" onSubmit={handleSubmit}>
      <label htmlFor="login-email">Email address</label><input id="login-email" type="email" autoComplete="username" required value={email} onChange={event => setEmail(event.target.value)} placeholder="you@hospital.example"/>
      <label htmlFor="login-password">Password</label><input id="login-password" type="password" autoComplete="current-password" required value={password} onChange={event => setPassword(event.target.value)} placeholder="Enter your password"/>
      {error && <p className="form-error" role="alert">{error}</p>}<button className="primary-button" type="submit" disabled={submitting}>{submitting ? 'Signing in…' : 'Sign in'}</button>
    </form>}
    <div className="auth-security"><ShieldCheck size={16}/><span>Protected by Supabase Auth and server-side role checks.</span></div>
    <p className="auth-disclaimer">Development system only. Do not enter real patient information until security and clinical workflows have been reviewed.</p>
  </section></main>
}
