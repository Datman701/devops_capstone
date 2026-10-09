import { useState } from 'react';
import AppointmentTable from '../components/AppointmentTable';
import BookingModal from '../components/BookingModal';
import Filters from '../components/Filters';
import { ErrorState, LoadingState } from '../components/states';
import { EMPTY_FILTERS, useAppointments } from '../hooks/useClinicData';

export default function AppointmentsPage({ reference }) {
  // `draftFilters` holds what the user is editing; `appliedFilters` is what the
  // list is actually fetched with. Keeping them separate means every keystroke
  // or dropdown change does not fire a request — only Apply does.
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState(EMPTY_FILTERS);
  const [showModal, setShowModal] = useState(false);
  const { doctors, patients } = reference;
  const { appointments, loading, error, busyId, advance, cancel, reload } = useAppointments(
    appliedFilters,
    reference.reload,
  );

  return (
    <div className="content">
      {error ? <ErrorState error={error} onRetry={reload} /> : null}

      <section className="panel">
        <div className="panel__head">
          <h2 className="panel__title">Filters</h2>
          <button
            type="button"
            className="btn btn--primary btn--sm"
            onClick={() => setShowModal(true)}
          >
            + Book appointment
          </button>
        </div>
        <div className="panel__body">
          <Filters
            filters={draftFilters}
            appliedFilters={appliedFilters}
            doctors={doctors}
            loading={loading}
            onChange={setDraftFilters}
            onApply={() => setAppliedFilters(draftFilters)}
            onReset={() => {
              setDraftFilters(EMPTY_FILTERS);
              setAppliedFilters(EMPTY_FILTERS);
            }}
          />
        </div>
      </section>

      <section className="panel">
        <div className="panel__head">
          <h2 className="panel__title">
            Appointments{' '}
            <span className="muted small">({appointments.length})</span>
          </h2>
          <button type="button" className="btn btn--sm" onClick={reload} disabled={loading}>
            {loading ? <span className="spinner" /> : 'Refresh'}
          </button>
        </div>
        {loading && !appointments.length ? (
          <LoadingState />
        ) : (
          <AppointmentTable
            appointments={appointments}
            onCancel={cancel}
            onAdvance={advance}
            busyId={busyId}
          />
        )}
      </section>

      {showModal ? (
        <BookingModal
          doctors={doctors}
          patients={patients}
          onClose={() => setShowModal(false)}
          onCreated={() => {
            setShowModal(false);
            reload();
          }}
        />
      ) : null}
    </div>
  );
}