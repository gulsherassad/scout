export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div className="status" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      {label}…
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="status status-error" role="alert">
      <strong>Something went wrong.</strong> {message}
      {onRetry && (
        <button type="button" className="btn-ghost" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}
