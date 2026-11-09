export default function StatCard({ label, value, hint, mono = false }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className={`stat-value${mono ? " mono" : ""}`} title={String(value)}>
        {value}
      </div>
      {hint && <div className="stat-hint">{hint}</div>}
    </div>
  );
}