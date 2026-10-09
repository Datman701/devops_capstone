import { STATUSES } from '../utils/format';

export default function Filters({
  filters,
  appliedFilters,
  doctors,
  onChange,
  onApply,
  onReset,
  loading,
}) {
  const update = (key) => (event) =>
    onChange({ ...filters, [key]: event.target.value });

  const dirty = Boolean(
    appliedFilters &&
      Object.keys(filters).some((key) => filters[key] !== appliedFilters[key]),
  );

  return (
    <div className="filters">
      <div className="field">
        <label className="field__label" htmlFor="filter-status">
          Status
        </label>
        <select
          id="filter-status"
          className="select select--sm"
          value={filters.status}
          onChange={update('status')}
        >
          {STATUSES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label className="field__label" htmlFor="filter-doctor">
          Doctor
        </label>
        <select
          id="filter-doctor"
          className="select select--sm"
          value={filters.doctor_id}
          onChange={update('doctor_id')}
        >
          <option value="">All doctors</option>
          {doctors.map((doctor) => (
            <option key={doctor.id} value={doctor.id}>
              {doctor.full_name}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label className="field__label" htmlFor="filter-from">
          From
        </label>
        <input
          id="filter-from"
          type="date"
          className="input input--sm"
          value={filters.date_from}
          onChange={update('date_from')}
        />
      </div>

      <div className="field">
        <label className="field__label" htmlFor="filter-to">
          To
        </label>
        <input
          id="filter-to"
          type="date"
          className="input input--sm"
          value={filters.date_to}
          onChange={update('date_to')}
        />
      </div>

      <div className="field">
        <label className="field__label" htmlFor="filter-upcoming">
          Upcoming
        </label>
        <select
          id="filter-upcoming"
          className="select select--sm"
          value={filters.upcoming_only}
          onChange={update('upcoming_only')}
        >
          <option value="">Any date</option>
          <option value="true">Upcoming only</option>
        </select>
      </div>

      <div className="filters__actions">
        <button
          type="button"
          className="btn btn--primary btn--sm"
          onClick={onApply}
          disabled={loading || !dirty}
        >
          Apply filter
        </button>
        <button type="button" className="btn btn--sm" onClick={onReset} disabled={loading}>
          Reset
        </button>
      </div>
    </div>
  );
}