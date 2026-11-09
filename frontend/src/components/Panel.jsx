import { AlertTriangle } from "lucide-react";

// A titled box that handles its own loading, error and empty states.
export default function Panel({ title, actions, note, error, loading, empty, className = "", children }) {
  let body = children;
  if (error) {
    body = (
      <p className="alert alert-error" role="alert">
        <AlertTriangle size={16} />
        <span>{error}</span>
      </p>
    );
  } else if (loading) {
    body = <p className="muted">Loading…</p>;
  } else if (empty) {
    body = <p className="muted">{empty}</p>;
  }

  const showNote = note && !error && !loading && !empty;

  return (
    <section className={`panel ${className}`}>
      <header className="panel-header">
        <h2>{title}</h2>
        {actions}
      </header>
      {body}
      {showNote && <p className="panel-note">{note}</p>}
    </section>
  );
}