import { CircleHelp } from 'lucide-react'

export function PlaceholderPage({ title, description }) {
  return <section className="page-wrap">
    <div className="page-heading"><div><div className="eyebrow">NEXUSCARE</div><h1>{title}</h1><p className="page-description">{description}</p></div></div>
    <div className="empty-state"><CircleHelp size={24}/><h2>This section is not available yet</h2><p>Its interactive workflow is not connected in this version.</p></div>
  </section>
}
