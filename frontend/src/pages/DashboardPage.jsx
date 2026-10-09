import { useState } from 'react';
import ActivityFeed from '../components/ActivityFeed';
import BookingModal from '../components/BookingModal';
import KpiCards from '../components/KpiCards';
import { ErrorState, LoadingState } from '../components/states';
import { useAppointments } from '../hooks/useClinicData';

/** Ranked list of doctors by appointment volume, with proportional bars. */
function BusyDoctors({ doctors }) {
  if (!doctors.length) {
    return <div className="muted small">No appointments recorded yet.</div>;
  }
  const max = Math.max(...doctors.map((doctor) => doctor.count));
  return (
    <div className="rank-list">
      {doctors.map((doctor) => (
        <div key={doctor.doctor_id}>
          <div className="rank-row">
            <div className="rank-row__name">
              {doctor.full_name}
              <div className="rank-row__specialty">{doctor.specialty}</div>
            </div>
            <div className="rank-row__count">{doctor.count}</div>
          </div>
          <div className="rank-row__track">
            <div
              style={{
                width: `${max ? (doctor.count / max) * 100 : 0}%`,
                height: '100%',
                background: 'var(--accent)',
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function DashboardPage({ reference }) {
  const [showModal, setShowModal] = useState(false);

  const upcoming = useAppointments({ upcoming_only: 'true', limit: 8 }, reference.reload);

  if (reference.loading && !reference.stats) {
    return (
      <div className="content">
        <LoadingState rows={5} />
      </div>
    );
  }

  if (reference.error && !reference.stats) {
    return (
      <div className="content">
        <ErrorState error={reference.error} onRetry={reference.reload} />
      </div>
    );
  }

  return (
    <div className="content">
      {reference.error ? (
        <ErrorState error={reference.error} onRetry={reference.reload} />
      ) : null}

      <KpiCards stats={reference.stats ?? { by_status: {} }} />

      <div className="split">
        <section className="panel">
          <div className="panel__head">
            <h2 className="panel__title">Upcoming schedule</h2>
            <button
              type="button"
              className="btn btn--primary btn--sm"
              onClick={() => setShowModal(true)}
            >
              + Book appointment
            </button>
          </div>
          <div className="panel__body">
            {upcoming.appointments.length === 0 ? (
              <div className="muted small">
                Nothing scheduled. Use “Book appointment” to add one.
              </div>
            ) : (
              <ul style={{ margin: 0, padding: 0, listStyle: 'none' }}>
                {upcoming.appointments.slice(0, 6).map((appointment) => (
                  <li
                    key={appointment.id}
                    className="feed__item"
                    style={{ borderBottom: '1px solid rgba(38,48,74,0.55)' }}
                  >
                    <div className="feed__body">
                      <div className="feed__title">
                        {appointment.patient.full_name} →{' '}
                        {appointment.doctor.full_name}
                      </div>
                      <div className="feed__meta">
                        {new Date(appointment.scheduled_at).toLocaleString()} ·{' '}
                        {appointment.status}
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button
                        type="button"
                        className="btn btn--sm"
                        disabled={upcoming.busyId === appointment.id}
                        onClick={() =>
                          upcoming.advance(
                            appointment.id,
                            appointment.status === 'scheduled'
                              ? 'confirmed'
                              : 'completed',
                          )
                        }
                      >
                        Advance
                      </button>
                      <button
                        type="button"
                        className="btn btn--sm btn--danger"
                        disabled={upcoming.busyId === appointment.id}
                        onClick={() => upcoming.cancel(appointment.id)}
                      >
                        Cancel
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>
          <section className="panel">
            <div className="panel__head">
              <h2 className="panel__title">Recent activity</h2>
            </div>
            <div className="panel__body">
              <ActivityFeed appointments={reference.stats?.latest ?? []} />
            </div>
          </section>

          <section className="panel">
            <div className="panel__head">
              <h2 className="panel__title">Doctor load</h2>
            </div>
            <div className="panel__body">
              <BusyDoctors doctors={reference.stats?.busy_doctors ?? []} />
            </div>
          </section>
        </div>
      </div>

      {showModal ? (
        <BookingModal
          doctors={reference.doctors}
          patients={reference.patients}
          onClose={() => setShowModal(false)}
          onCreated={() => {
            setShowModal(false);
            upcoming.reload();
          }}
        />
      ) : null}
    </div>
  );
}