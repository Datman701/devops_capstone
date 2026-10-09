import { useState } from 'react';
import { api } from '../api/client';
import { ErrorState, LoadingState } from '../components/states';
import { formatCurrency } from '../utils/format';

const BLANK = { full_name: '', specialty: '', email: '', consultation_fee: '' };

export default function DoctorsPage({ reference }) {
  const { doctors, loading, error, reload } = reference;
  const [form, setForm] = useState(BLANK);
  const [formError, setFormError] = useState('');
  const [saving, setSaving] = useState(false);

  const update = (key) => (event) =>
    setForm((previous) => ({ ...previous, [key]: event.target.value }));

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setFormError('');
    try {
      await api.createDoctor({
        full_name: form.full_name,
        specialty: form.specialty,
        email: form.email,
        consultation_fee: Number(form.consultation_fee || 0),
      });
      setForm(BLANK);
      reload();
    } catch (err) {
      setFormError(err.message ?? 'Could not create the doctor.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="content">
      {error ? <ErrorState error={error} onRetry={reload} /> : null}

      <div className="split">
        <section className="panel">
          <div className="panel__head">
            <h2 className="panel__title">Doctors ({doctors.length})</h2>
          </div>
          {loading && !doctors.length ? (
            <LoadingState />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Specialty</th>
                    <th>Email</th>
                    <th className="right">Fee</th>
                  </tr>
                </thead>
                <tbody>
                  {doctors.map((doctor) => (
                    <tr key={doctor.id}>
                      <td className="cell-strong">{doctor.full_name}</td>
                      <td>{doctor.specialty}</td>
                      <td className="cell-muted">{doctor.email}</td>
                      <td className="right">
                        {formatCurrency(doctor.consultation_fee)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel__head">
            <h2 className="panel__title">Add doctor</h2>
          </div>
          <div className="panel__body">
            <form
              onSubmit={handleSubmit}
              style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
            >
              {formError ? <div className="form-error">{formError}</div> : null}
              <div className="field">
                <label className="field__label" htmlFor="doc-name">
                  Full name
                </label>
                <input
                  id="doc-name"
                  className="input"
                  value={form.full_name}
                  onChange={update('full_name')}
                  placeholder="Dr. Anita Rao"
                  required
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="doc-specialty">
                  Specialty
                </label>
                <input
                  id="doc-specialty"
                  className="input"
                  value={form.specialty}
                  onChange={update('specialty')}
                  placeholder="Cardiology"
                  required
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="doc-email">
                  Email
                </label>
                <input
                  id="doc-email"
                  type="email"
                  className="input"
                  value={form.email}
                  onChange={update('email')}
                  placeholder="name@clinicdesk.test"
                  required
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="doc-fee">
                  Consultation fee
                </label>
                <input
                  id="doc-fee"
                  type="number"
                  min="0"
                  className="input"
                  value={form.consultation_fee}
                  onChange={update('consultation_fee')}
                  placeholder="750"
                />
              </div>
              <button type="submit" className="btn btn--primary" disabled={saving}>
                {saving ? (
                  <>
                    <span className="spinner" /> Saving
                  </>
                ) : (
                  'Add doctor'
                )}
              </button>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}