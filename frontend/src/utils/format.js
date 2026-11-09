export function formatNumber(value) {
  return new Intl.NumberFormat().format(value);
}

// SQLite's CURRENT_TIMESTAMP is UTC text like "2026-11-09 08:15:00" with no timezone marker,
// so we add the "Z" ourselves before parsing.
export function formatRelativeTime(sqliteTimestamp) {
  const then = new Date(String(sqliteTimestamp).replace(" ", "T") + "Z");
  const seconds = Math.round((Date.now() - then.getTime()) / 1000);
  if (Number.isNaN(seconds) || seconds < 60) return "just now";

  const units = [
    ["day", 86400],
    ["hour", 3600],
    ["minute", 60],
  ];
  for (const [unit, size] of units) {
    if (seconds >= size) {
      const count = Math.floor(seconds / size);
      return `${count} ${unit}${count > 1 ? "s" : ""} ago`;
    }
  }
  return "just now";
}