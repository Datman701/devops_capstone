export default function Topbar({ title, subtitle, actions, onToggleSidebar }) {
  return (
    <header className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <button
          type="button"
          className="sidebar-toggle"
          onClick={onToggleSidebar}
          aria-label="Toggle navigation"
        >
          ☰
        </button>
        <div>
          <h1 className="topbar__title">{title}</h1>
          <p className="topbar__subtitle">{subtitle}</p>
        </div>
      </div>
      {actions ? <div className="topbar__actions">{actions}</div> : null}
    </header>
  );
}