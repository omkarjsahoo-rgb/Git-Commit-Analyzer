import { Bar } from "react-chartjs-2";
import "./chartSetup.js";
import { COLORS, baseOptions } from "./chartTheme.js";

export default function ActivityChart({ labels, commits, label = "Commits" }) {
  const data = {
    labels,
    datasets: [
      {
        label,
        data: commits,
        backgroundColor: COLORS.green,
        borderRadius: 2,
        maxBarThickness: 28,
      },
    ],
  };

  const options = {
    ...baseOptions,
    scales: {
      x: {
        grid: { display: false },
        border: { color: COLORS.border },
        ticks: { maxTicksLimit: 8, maxRotation: 0 },
      },
      y: {
        beginAtZero: true,
        grid: { color: COLORS.border },
        border: { display: false },
        ticks: { precision: 0 },
      },
    },
  };

  return (
    <div className="chart-box">
      <Bar data={data} options={options} />
    </div>
  );
}