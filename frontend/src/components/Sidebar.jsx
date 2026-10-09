import { NavLink } from 'react-router-dom';

const LINKS = [
  { to: '/', label: 'Dashboard', icon: '▤', end: true },
  { to: '/appointments', label: 'Appointments', icon: '☰', end: false },
  { to: '/doctors', label: 'Doctors', icon: '✚', end: false },
  { to: '/patients', label: 'Patients', icon: '☺', end: false },
];

export default function Sidebar({ isOpen, onNavigate, backendUp }) {
  return (
    <aside className={`sidebar ${isOpen ? 'is-open' : ''}`}>
      <div className="sidebar__brand">
        <div className="sidebar__logo">C</div>
        <div>
          <div className="sidebar__title">ClinicDesk</div>
          <div className="sidebar__subtitle">Operations console</div>
        </div>
      </div>

      <div className="sidebar__section">Workspace</div>
      <nav className="sidebar__nav">
        {LINKS.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              `sidebar__link ${isActive ? 'is-active' : ''}`
            }
          >
            <span className="sidebar__icon" aria-hidden="true">{link.icon}</span>
            {link.label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar__footer">
        <span
          className={`health-dot ${
            backendUp ? 'health-dot--up' : 'health-dot--down'
          }`}
        />
        {backendUp ? 'API connected' : 'API unreachable'}
      </div>
    </aside>
  );
}