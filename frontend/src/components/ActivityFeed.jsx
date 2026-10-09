import { STATUS_LABELS, formatDateTime, relativeTime } from '../utils/format';

const MARKERS = {
  scheduled: '',
  confirmed: 'feed__marker--success',
  completed: 'feed__marker--muted',
  cancelled: 'feed__marker--danger',
  no_show: 'feed__marker--warn',
};

/**
 * Renders GET /appointments/stats -> `latest`, which is a flat summary shape
 * (patient_name / doctor_name) rather than the nested appointment shape used
 * by the appointments table.
 */
export default function ActivityFeed({ appointments }) {
  if (!appointments.length) {
    return <div className="muted small">No recent activity yet.</div>;
  }

  return (
    <div className="feed">
      {appointments.map((appointment) => (
        <div className="feed__item" key={appointment.id}>
          <span className={`feed__marker ${MARKERS[appointment.status] ?? ''}`} />
          <div className="feed__body">
            <div className="feed__title">
              {appointment.patient_name} with {appointment.doctor_name}
            </div>
            <div className="feed__meta">
              {formatDateTime(appointment.scheduled_at)} ·{' '}
              {STATUS_LABELS[appointment.status] ?? appointment.status} · created{' '}
              {relativeTime(appointment.created_at)}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}