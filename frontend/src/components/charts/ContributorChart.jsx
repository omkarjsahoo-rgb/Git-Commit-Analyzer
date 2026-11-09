import { Bar } from "react-chartjs-2";
import "./chartSetup.js";
import { COLORS, baseOptions } from "./chartTheme.js";

const MAX_BARS = 8;

export default function ContributorChart({ contributors }) {
  const top = contributors.slice(0, MAX_BARS);

  const data = {
    labels: top.map((c) => c.name),
    datasets: [
      {
        label: "Commits",
        data: top.map((c) => c.commits),
        backgroundColor: COLORS.green,
        borderRadius: 2,
        maxBarThickness: 22,
      },
    ],
  };

  const options = {
    ...baseOptions,
    indexAxis: "y", // horizontal bars, so long names stay readable
    plugins: {
      tooltip: {
        ...baseOptions.plugins.tooltip,
        callbacks: {
          label: (ctx) => `${ctx.parsed.x} commits (${top[ctx.dataIndex].percent}%)`,
        },
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

  // Grow the box with the number of bars so they never look squashed.
  const height = Math.max(120, top.length * 34 + 40);

  return (
    <div className="chart-box" style={{ height }}>
      <Bar data={data} options={options} />
    </div>
  );
}