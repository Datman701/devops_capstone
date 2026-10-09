import { useState } from 'react';
import { api } from '../api/client';
import { ErrorState, LoadingState } from '../components/states';

const BLANK = { full_name: '', phone: '', email: '' };

export default function PatientsPage({ reference }) {
  const { patients, loading, error, reload } = reference;
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
      await api.createPatient({
        full_name: form.full_name,
        phone: form.phone,
        email: form.email || null,
      });
      setForm(BLANK);
      reload();
    } catch (err) {
      setFormError(err.message ?? 'Could not register the patient.');
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
            <h2 className="panel__title">Patients ({patients.length})</h2>
          </div>
          {loading && !patients.length ? (
            <LoadingState />
          ) : (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Phone</th>
                    <th>Email</th>
                  </tr>
                </thead>
                <tbody>
                  {patients.map((patient) => (
                    <tr key={patient.id}>
                      <td className="cell-strong">{patient.full_name}</td>
                      <td>{patient.phone}</td>
                      <td className="cell-muted">{patient.email || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel__head">
            <h2 className="panel__title">Register patient</h2>
          </div>
          <div className="panel__body">
            <form
              onSubmit={handleSubmit}
              style={{ display: 'flex', flexDirection: 'column', gap: 12 }}
            >
              {formError ? <div className="form-error">{formError}</div> : null}
              <div className="field">
                <label className="field__label" htmlFor="pat-name">
                  Full name
                </label>
                <input
                  id="pat-name"
                  className="input"
                  value={form.full_name}
                  onChange={update('full_name')}
                  placeholder="Meera Iyer"
                  required
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="pat-phone">
                  Phone
                </label>
                <input
                  id="pat-phone"
                  className="input"
                  value={form.phone}
                  onChange={update('phone')}
                  placeholder="+91 98450 11223"
                  required
                />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="pat-email">
                  Email (optional)
                </label>
                <input
                  id="pat-email"
                  type="email"
                  className="input"
                  value={form.email}
                  onChange={update('email')}
                  placeholder="patient@clinicdesk.test"
                />
              </div>
              <button type="submit" className="btn btn--primary" disabled={saving}>
                {saving ? (
                  <>
                    <span className="spinner" /> Saving
                  </>
                ) : (
                  'Register patient'
                )}
              </button>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}