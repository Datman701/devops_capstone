export function LoadingState({ rows = 4 }) {
  return (
    <div style={{ padding: 16, display: 'flex', flexDirection: 'column', gap: 10 }}>
      {Array.from({ length: rows }).map((_, index) => (
        <div
          key={index}
          className="skeleton"
          style={{ height: 34, opacity: 1 - index * 0.15 }}
        />
      ))}
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="alert alert--error">
      <span aria-hidden="true">⚠</span>
      <div style={{ flex: 1 }}>
        <strong>Could not reach the backend.</strong>
        <div style={{ marginTop: 3, opacity: 0.9 }}>
          {error?.message ?? 'Unexpected error'} — is the API running?
        </div>
      </div>
      {onRetry ? (
        <button type="button" className="btn btn--sm" onClick={onRetry}>
          Retry
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, message }) {
  return (
    <div className="empty">
      <div className="empty__title">{title}</div>
      <div>{message}</div>
    </div>
  );
}