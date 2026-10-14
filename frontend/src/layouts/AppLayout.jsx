import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Menu, Moon, Sun, Bell, HeartPulse, LogOut, CheckCheck } from 'lucide-react'
import { Sidebar } from '../components/navigation/Sidebar.jsx'
import { apiRequest } from '../lib/api.js'

function NotificationCenter() {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
  const notifications = useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: () => apiRequest('/notifications?unread_only=true'),
    refetchInterval: 30000,
  })
  const markRead = useMutation({
    mutationFn: id => apiRequest('/notifications/' + id + '/read', { method: 'PATCH' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })
  const rows = notifications.data || []
  return <div className="notification-center">
    <button className="icon-button notification-trigger" aria-label={rows.length ? `Notifications, ${rows.length} unread` : 'Notifications'} aria-expanded={open} onClick={() => setOpen(value => !value)}>
      <Bell size={17}/>{rows.length > 0 && <span className="notification-count">{rows.length > 9 ? '9+' : rows.length}</span>}
    </button>
    {open && <section className="notification-panel" aria-label="Notifications">
      <div className="notification-panel-heading"><strong>Notifications</strong><span>{rows.length} unread</span></div>
      {notifications.isPending ? <p className="notification-message">Loading notifications…</p>
        : notifications.isError ? <p className="notification-message">{notifications.error.message}</p>
        : rows.length === 0 ? <p className="notification-message">You're all caught up.</p>
        : rows.map(item => <button className="notification-item" key={item.id} onClick={() => markRead.mutate(item.id)} disabled={markRead.isPending}>
            <span className="notification-unread-dot"/>
            <span className="notification-item-copy"><strong>{item.title}</strong><span>{item.message}</span><small>{item.created_at ? new Date(item.created_at).toLocaleString() : ''}</small></span>
            <CheckCheck size={14}/>
          </button>)}
    </section>}
  </div>
}

export function AppLayout({ children, theme, onToggleTheme, userEmail, onSignOut, roles = [] }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  return <div className="app-frame">
    <Sidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} userEmail={userEmail} roles={roles}/>
    {mobileOpen && <button className="drawer-scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)}/>}
    <div className="main-column">
      <header className="topbar">
        <button className="icon-button mobile-menu-button" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={19}/></button>
        <div className="breadcrumb"><span>Workspace</span><span>/</span><strong>NexusCare</strong></div>
        <div className="topbar-actions">
          <NotificationCenter/>
          <button className="icon-button" aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'} onClick={onToggleTheme}>{theme === 'dark' ? <Sun size={17}/> : <Moon size={17}/>}</button>
          <button className="icon-button" aria-label="Sign out" title={userEmail || 'Sign out'} onClick={onSignOut}><LogOut size={17}/></button>
        </div>
      </header>
      <main className="main-content">{children}</main>
      <footer className="app-footer"><span><HeartPulse size={14}/> NexusCare</span></footer>
    </div>
  </div>
}
