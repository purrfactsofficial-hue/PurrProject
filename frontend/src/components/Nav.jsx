import { NavLink } from 'react-router-dom'
import './Nav.css'

const NAV_ITEMS = [
  { to: '/', icon: '▦', label: 'Library' },
  { to: '/episode', icon: '✎', label: 'Episode' },
  { to: '/queue', icon: '◴', label: 'Queue' },
  { to: '/dashboard', icon: '◷', label: 'Dashboard' },
  { to: '/settings', icon: '⚙', label: 'Settings' },
]

export default function Nav() {
  return (
    <aside className="side">
      <div className="brand">
        <div className="bell" aria-hidden="true" />
        <div className="brand-text">
          <h1>PurrFacts</h1>
          <small>Studio</small>
        </div>
      </div>
      <nav>
        {NAV_ITEMS.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => isActive ? 'active' : undefined}
          >
            <span className="ic">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="side-foot">
        Signed in as<br /><b>borodulina.iana</b>
      </div>
    </aside>
  )
}
