"use client";

import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';
import ActivityFeed from '../components/ActivityFeed';
import BookingModal from '../components/BookingModal';
import KpiCards from '../components/KpiCards';
import { ErrorState, LoadingState } from '../components/states';

// Custom hook for reference data (doctors, patients, stats)
export function useReferenceData() {
  const [doctors, setDoctors] = useState([]);
  const [patients, setPatients] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [backendUp, setBackendUp] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [doctorList, patientList, statsData] = await Promise.all([
        api.listDoctors(),
        api.listPatients(),
        api.getStats(),
      ]);
      setDoctors(doctorList);
      setPatients(patientList);
      setStats(statsData);
      setBackendUp(true);
    } catch (err) {
      setError(err);
      setBackendUp(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  // Poll the liveness endpoint so the sidebar indicator reflects reality.
  useEffect(() => {
    let stopped = false;
    const check = () => {
      api
        .health()
        .then(() => !stopped && setBackendUp(true))
        .catch(() => !stopped && setBackendUp(false));
    };
    const timer = setInterval(check, 15000);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, []);

  return { doctors, patients, stats, loading, error, backendUp, reload: load };
}

const EMPTY_FILTERS = {
  status: '',
  doctor_id: '',
  date_from: '',
  date_to: '',
  upcoming_only: '',
};

// Custom hook for appointment list with filters
export function useAppointments(filters = {}, onChanged) {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = {
        status: filters.status || undefined,
        doctor_id: filters.doctor_id || undefined,
        date_from: filters.date_from
          ? new Date(`${filters.date_from}T00:00:00`).toISOString()
          : undefined,
        date_to: filters.date_to
          ? new Date(`${filters.date_to}T23:59:59`).toISOString()
          : undefined,
        upcoming_only: filters.upcoming_only || undefined,
        limit: 100,
      };
      setAppointments(await api.listAppointments(params));
    } catch (err) {
      setError(err);
      setAppointments([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  const refreshAll = useCallback(async () => {
    await Promise.all([load(), onChanged?.()]);
  }, [load, onChanged]);

  const advance = useCallback(
    async (id, status) => {
      setBusyId(id);
      try {
        await api.changeStatus(id, status);
        await refreshAll();
      } catch (err) {
        setError(err);
      } finally {
        setBusyId(null);
      }
    },
    [refreshAll],
  );

  const cancel = useCallback(
    async (id) => {
      setBusyId(id);
      try {
        await api.cancelAppointment(id);
        await refreshAll();
      } catch (err) {
        setError(err);
      } finally {
        setBusyId(null);
      }
    },
    [refreshAll],
  );

  return {
    appointments,
    loading,
    error,
    busyId,
    reload: refreshAll,
    advance,
    cancel,
  };
}

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

export default function DashboardPage() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const reference = useReferenceData();
  const [showModal, setShowModal] = useState(false);

  const upcoming = useAppointments({ upcoming_only: 'true', limit: 8 }, reference.reload);
  const all = useAppointments({}, reference.reload);

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
      <ErrorState error={reference.error} onRetry={reference.reload} />

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