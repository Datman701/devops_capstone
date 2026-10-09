import { useEffect, useMemo, useState } from 'react';
import { api } from '../api/client';
import { toLocalInputValue } from '../utils/format';

function defaultDateTime() {
  const date = new Date(Date.now() + 24 * 60 * 60 * 1000);
  date.setMinutes(0, 0, 0);
  date.setHours(Math.min(Math.max(date.getHours(), 9), 17));
  const pad = (value) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(
    date.getHours(),
  )}:${pad(date.getMinutes())}`;
}

export default function BookingModal({
  onClose,
  onCreated,
  doctors,
  patients,
  appointment = null,
}) {
  const editing = Boolean(appointment);
  const [form, setForm] = useState(() => ({
    doctor_id: appointment?.doctor_id ?? doctors[0]?.id ?? '',
    patient_id: appointment?.patient_id ?? patients[0]?.id ?? '',
scheduled_at: appointment
      ? toLocalInputValue(appointment.scheduled_at)
      : defaultDateTime(),
    duration_minutes: appointment?.duration_minutes ?? 30,
    reason: appointment?.reason ?? '',
    notes: appointment?.notes ?? '',
  }));
  const [newPatient, setNewPatient] = useState({ full_name: '', phone: '' });
  const [showNewPatient, setShowNewPatient] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [freeSlots, setFreeSlots] = useState([]);

  const update = (key) => (event) =>
    setForm((previous) => ({ ...previous, [key]: event.target.value }));

  // Offer the selected doctor's genuinely free 30-minute slots.
  useEffect(() => {
    if (!form.doctor_id) return undefined;
    let cancelled = false;
    api
      .availability(form.doctor_id, new Date(form.scheduled_at).toISOString())
      .then((data) => {
        if (!cancelled) setFreeSlots(data.free_slots ?? []);
      })
      .catch(() => {
        if (!cancelled) setFreeSlots([]);
      });
    return () => {
      cancelled = true;
    };
  }, [form.doctor_id, form.scheduled_at]);

  const selectedDoctor = useMemo(
    () => doctors.find((doctor) => doctor.id === Number(form.doctor_id)),
    [doctors, form.doctor_id],
  );

  async function handleSubmit(event) {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      let patientId = Number(form.patient_id);
      if (showNewPatient) {
        const created = await api.createPatient({
          full_name: newPatient.full_name,
          phone: newPatient.phone,
        });
        patientId = created.id;
      }

      const payload = {
        doctor_id: Number(form.doctor_id),
        patient_id: patientId,
        scheduled_at: new Date(form.scheduled_at).toISOString(),
        duration_minutes: Number(form.duration_minutes),
        reason: form.reason || null,
        notes: form.notes || null,
      };

      const saved = editing
        ? await api.updateAppointment(appointment.id, payload)
        : await api.createAppointment(payload);

      onCreated(saved);
    } catch (err) {
      if (err.status === 409) {
        setError(
          `${err.message} Pick one of the free slots listed below the field.`,
        );
      } else {
        setError(err.message ?? 'Could not save the appointment.');
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="modal-backdrop"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="modal" role="dialog" aria-modal="true" aria-label="Appointment">
        <div className="modal__head">
          <h2 className="modal__title">
            {editing ? `Reschedule #${appointment.id}` : 'Book appointment'}
          </h2>
          <button type="button" className="btn btn--sm" onClick={onClose}>
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal__body">
            {error ? <div className="form-error">{error}</div> : null}

            <div className="field">
              <label className="field__label" htmlFor="modal-doctor">
                Doctor
              </label>
              <select
                id="modal-doctor"
                className="select"
                value={form.doctor_id}
                onChange={update('doctor_id')}
                required
              >
                {doctors.length === 0 && <option value="">No doctors available</option>}
                {doctors.map((doctor) => (
                  <option key={doctor.id} value={doctor.id}>
                    {doctor.full_name} — {doctor.specialty}
                  </option>
                ))}
              </select>
              {selectedDoctor ? (
                <span className="muted small">
                  Consultation fee {selectedDoctor.consultation_fee}
                </span>
              ) : null}
            </div>

            <div className="field">
              <label className="field__label" htmlFor="modal-patient">
                Patient
              </label>
              <select
                id="modal-patient"
                className="select"
                value={form.patient_id}
                onChange={update('patient_id')}
                required
                disabled={showNewPatient}
              >
                {patients.length === 0 && <option value="">No patients yet</option>}
                {patients.map((patient) => (
                  <option key={patient.id} value={patient.id}>
                    {patient.full_name} — {patient.phone}
                  </option>
                ))}
              </select>
              {!editing ? (
                <button
                  type="button"
                  className="btn btn--sm"
                  onClick={() => setShowNewPatient((value) => !value)}
                  style={{ alignSelf: 'flex-start' }}
                >
                  {showNewPatient ? 'Choose existing patient' : '+ Register new patient'}
                </button>
              ) : null}
            </div>

            {showNewPatient && !editing ? (
              <div className="form-row">
                <div className="field">
                  <label className="field__label" htmlFor="modal-new-name">
                    Patient name
                  </label>
                  <input
                    id="modal-new-name"
                    className="input"
                    value={newPatient.full_name}
                    onChange={(event) =>
                      setNewPatient((previous) => ({
                        ...previous,
                        full_name: event.target.value,
                      }))
                    }
                    required
                  />
                </div>
                <div className="field">
                  <label className="field__label" htmlFor="modal-new-phone">
                    Phone
                  </label>
                  <input
                    id="modal-new-phone"
                    className="input"
                    value={newPatient.phone}
                    onChange={(event) =>
                      setNewPatient((previous) => ({
                        ...previous,
                        phone: event.target.value,
                      }))
                    }
                    required
                  />
                </div>
              </div>
            ) : null}

            <div className="form-row">
              <div className="field">
                <label className="field__label" htmlFor="modal-when">
                  Date &amp; time
                </label>
                <input
                  id="modal-when"
                  type="datetime-local"
                  className="input"
                  value={form.scheduled_at}
                  onChange={update('scheduled_at')}
                  required
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="modal-duration">
                  Duration (min)
                </label>
                <select
                  id="modal-duration"
                  className="select"
                  value={form.duration_minutes}
                  onChange={update('duration_minutes')}
                >
                  {[15, 30, 45, 60, 90].map((value) => (
                    <option key={value} value={value}>
                      {value} minutes
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {freeSlots.length ? (
              <div className="field">
                <span className="field__label">Free slots that day</span>
                <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  {freeSlots.slice(0, 8).map((slot) => (
                    <button
                      key={slot}
                      type="button"
                      className="btn btn--sm"
                      onClick={() =>
                        setForm((previous) => ({
                          ...previous,
                          scheduled_at: toLocalInputValue(slot),
                        }))
                      }
                    >
                      {new Date(slot).toLocaleTimeString(undefined, {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}

            <div className="field">
              <label className="field__label" htmlFor="modal-reason">
                Reason
              </label>
              <input
                id="modal-reason"
                className="input"
                value={form.reason}
                onChange={update('reason')}
                placeholder="Follow-up consultation"
              />
            </div>

            <div className="field">
              <label className="field__label" htmlFor="modal-notes">
                Notes
              </label>
              <input
                id="modal-notes"
                className="input"
                value={form.notes}
                onChange={update('notes')}
                placeholder="Optional internal note"
              />
            </div>
          </div>

          <div className="modal__foot">
            <button type="button" className="btn" onClick={onClose} disabled={submitting}>
              Close
            </button>
            <button type="submit" className="btn btn--primary" disabled={submitting}>
              {submitting ? (
                <>
                  <span className="spinner" /> Saving
                </>
              ) : editing ? (
                'Save changes'
              ) : (
                'Book appointment'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}