import { ArrowUpRight, CircleHelp, Clock3 } from 'lucide-react'

export function PlaceholderPage({ title, description }) {
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">NEXUSCARE WORKSPACE</div><h1>{title}</h1><p className="page-description">{description}</p></div><span className="phase-tag"><Clock3 size={13}/> API available</span></div>
    <div className="starter-panel"><div className="panel-icon"><CircleHelp size={20}/></div><div className="panel-copy"><h2>Backend workflow available</h2><p>The FastAPI endpoints for this module are implemented, but this dedicated interactive screen is not finished yet. Use the authenticated API documentation at <code>/docs</code> to exercise the endpoints while the UI is being connected.</p><div className="panel-meta"><span className="mini-status-dot"/> API access remains role-protected</div></div><ArrowUpRight className="panel-arrow" size={17}/></div>
    <div className="section-heading"><h2>Implementation status</h2><span>BACKEND FIRST</span></div>
    <div className="notes-grid"><article className="note-card"><span className="note-number">01</span><h3>Real API</h3><p>This module uses the centralized FastAPI and Supabase PostgreSQL data model; no permanent mock records are displayed here.</p></article><article className="note-card"><span className="note-number">02</span><h3>Access controlled</h3><p>The API checks the authenticated profile and role. Hiding a navigation item is not treated as a security boundary.</p></article><article className="note-card"><span className="note-number">03</span><h3>UI remaining</h3><p>Forms, filters, workflow actions, loading states, and role-specific table screens still need to be connected for this module.</p></article></div>
    <div className="disclaimer">Development environment only · Use fictional data. This placeholder is not a substitute for a completed hospital workflow screen.</div>
  </section>
}
