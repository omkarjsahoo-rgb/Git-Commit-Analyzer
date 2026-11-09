import { Bar } from "react-chartjs-2";
import "./chartSetup.js";
import { COLORS, baseOptions } from "./chartTheme.js";

const BUCKETS = [
  { key: "excellent", label: "Excellent (80+)", color: COLORS.green },
  { key: "good", label: "Good (60–79)", color: COLORS.greenLight },
  { key: "fair", label: "Fair (40–59)", color: COLORS.warning },
  { key: "poor", label: "Poor (under 40)", color: COLORS.error },
];

export default function QualityChart({ distribution }) {
  const data = {
    labels: BUCKETS.map((b) => b.label),
    datasets: [
      {
        label: "Commits",
        data: BUCKETS.map((b) => distribution[b.key]),
        backgroundColor: BUCKETS.map((b) => b.color),
        borderRadius: 2,
        maxBarThickness: 22,
      },
    ],
  };

  const options = {
    ...baseOptions,
    indexAxis: "y",
    plugins: {
      tooltip: {
        ...baseOptions.plugins.tooltip,
        callbacks: { label: (ctx) => `${ctx.parsed.x} commits` },
      },
    },
    scales: {
      x: {
        beginAtZero: true,
        grid: { color: COLORS.border },
        border: { display: false },
        ticks: { precision: 0 },
      },
      y: { grid: { display: false }, border: { color: COLORS.border } },
    },
  };

  return (
    <div className="chart-box" style={{ height: 190 }}>
      <Bar data={data} options={options} />
    </div>
  );
}