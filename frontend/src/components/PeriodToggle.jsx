const PERIODS = [
  { id: "daily", label: "Daily" },
  { id: "weekly", label: "Weekly" },
  { id: "monthly", label: "Monthly" },
];

export default function PeriodToggle({ value, onChange }) {
  return (
    <div className="segmented" role="group" aria-label="Time period">
      {PERIODS.map((item) => (
        <button
          key={item.id}
          type="button"
          className={`segmented-btn${item.id === value ? " is-active" : ""}`}
          aria-pressed={item.id === value}
          onClick={() => onChange(item.id)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}