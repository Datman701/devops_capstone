function KpiCard({ label, value, hint, segments = null }) {
  return (
    <article className="kpi-card">
      <span className="kpi-card__label">{label}</span>
      <span className="kpi-card__value">{value}</span>
      {hint ? <span className="kpi-card__hint">{hint}</span> : null}
      {segments ? (
        <div className="kpi-card__bar" aria-hidden="true">
          {segments.map((segment, index) => (
            <span
              key={index}
              className={`kpi-card__seg ${
                segment.filled ? 'kpi-card__seg--filled' : ''
              }`}
              style={segment.color ? { background: segment.color } : undefined}
            />
          ))}
        </div>
      ) : null}
    </article>
  );
}

export default function KpiCards({ stats }) {
  const byStatus = stats.by_status ?? {};
  const statuses = ['scheduled', 'confirmed', 'completed', 'cancelled', 'no_show'];
  const total = stats.total || 0;
  const colours = {
    scheduled: '#4f8cff',
    confirmed: '#2fb37a',
    completed: '#8f9bb3',
    cancelled: '#e5484d',
    no_show: '#e0a325',
  };

  const segments = total
    ? statuses.map((status) => ({
        filled: (byStatus[status] ?? 0) > 0,
        color: (byStatus[status] ?? 0) > 0 ? colours[status] : undefined,
      }))
    : null;

  return (
    <section className="kpi-grid">
      <KpiCard
        label="Appointments"
        value={stats.total ?? 0}
        hint={`${stats.active_doctors ?? 0} doctors on roster`}
        segments={segments}
      />
      <KpiCard
        label="Today"
        value={stats.today ?? 0}
        hint="Scheduled for today"
      />
      <KpiCard
        label="Next 7 days"
        value={stats.upcoming_7_days ?? 0}
        hint="Confirmed or scheduled"
      />
      <KpiCard
        label="Cancelled"
        value={`${Math.round((stats.cancelled_rate ?? 0) * 100)}%`}
        hint={
          stats.busiest_hour !== null && stats.busiest_hour !== undefined
            ? `Busiest hour ${String(stats.busiest_hour).padStart(2, '0')}:00`
            : 'No data yet'
        }
      />
      <KpiCard
        label="Patients"
        value={stats.active_patients ?? 0}
        hint="Registered in directory"
      />
    </section>
  );
}