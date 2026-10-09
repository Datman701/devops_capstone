import { NEXT_STATUSES, STATUS_LABELS, formatDateTime } from '../utils/format';

function StatusBadge({ status }) {
  const classes = {
    scheduled: 'badge badge--info',
    confirmed: 'badge badge--success',
    completed: 'badge badge--muted',
    cancelled: 'badge badge--danger',
    no_show: 'badge badge--warn',
  };
  return (
    <span className={classes[status] ?? 'badge badge--muted'}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

export default function AppointmentTable({
  appointments,
  onCancel,
  onAdvance,
  busyId,
}) {
  if (!appointments.length) {
    return (
      <div className="empty">
        <div className="empty__title">No appointments found</div>
        Adjust the filters or book a new appointment.
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Patient</th>
            <th>Doctor</th>
            <th>Scheduled</th>
            <th>Reason</th>
            <th>Status</th>
            <th className="right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {appointments.map((appointment) => {
            const next = NEXT_STATUSES[appointment.status] ?? [];
            const isBusy = busyId === appointment.id;
            return (
              <tr key={appointment.id}>
                <td>
                  <div className="cell-strong">{appointment.patient.full_name}</div>
                  <div className="cell-muted">{appointment.patient.phone}</div>
                </td>
                <td>
                  <div className="cell-strong">{appointment.doctor.full_name}</div>
                  <div className="cell-muted">{appointment.doctor.specialty}</div>
                </td>
                <td className="nowrap">{formatDateTime(appointment.scheduled_at)}</td>
                <td className="cell-muted">{appointment.reason || '-'}</td>
                <td>
                  <StatusBadge status={appointment.status} />
                </td>
                <td>
                  <div className="table__actions">
                    {next
                      .filter((status) => status !== 'cancelled')
                      .slice(0, 1)
                      .map((status) => (
                        <button
                          key={status}
                          type="button"
                          className="btn btn--sm"
                          disabled={isBusy}
                          onClick={() => onAdvance(appointment.id, status)}
                        >
                          {isBusy ? (
                            <span className="spinner" />
                          ) : (
                            `Mark ${STATUS_LABELS[status].toLowerCase()}`
                          )}
                        </button>
                      ))}
                    {next.includes('cancelled') ? (
                      <button
                        type="button"
                        className="btn btn--sm btn--danger"
                        disabled={isBusy}
                        onClick={() => onCancel(appointment.id)}
                      >
                        Cancel
                      </button>
                    ) : null}
                  </div>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export { StatusBadge };