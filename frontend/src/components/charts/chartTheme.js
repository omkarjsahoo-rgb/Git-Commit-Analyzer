// Chart.js draws on a <canvas>, which cannot read CSS variables,
// so these values repeat the palette from theme.css.
export const COLORS = {
  green: "#22c55e",
  greenLight: "#86efac",
  text: "#e5e7eb",
  muted: "#8b968e",
  border: "#26352b",
  panel: "#101713",
  warning: "#eab308",
  error: "#ef4444",
};

export const baseOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    tooltip: {
      backgroundColor: COLORS.panel,
      borderColor: COLORS.border,
      borderWidth: 1,
      titleColor: COLORS.text,
      bodyColor: COLORS.text,
      padding: 10,
      displayColors: false,
    },
  },
};