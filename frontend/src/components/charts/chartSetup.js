import { BarElement, CategoryScale, Chart as ChartJS, LinearScale, Tooltip } from "chart.js";
import { COLORS } from "./chartTheme.js";

// Chart.js only includes the parts you register. We only draw bar charts.
ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

ChartJS.defaults.color = COLORS.muted;
ChartJS.defaults.font.family = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';
ChartJS.defaults.font.size = 12;