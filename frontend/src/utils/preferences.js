const STORAGE_KEY = "gca.preferences";

export const PERIOD_CHOICES = ["daily", "weekly", "monthly"];
export const INACTIVE_DAY_CHOICES = [14, 30, 60, 90, 180];
export const PAGE_SIZE_CHOICES = [10, 25, 50, 100];

export const DEFAULT_PREFERENCES = { period: "weekly", inactiveDays: 30, pageSize: 25 };

// Only accept values from the allowed lists, so a hand-edited or corrupted browser store
// can never send nonsense (like a page size of 99999) to the backend.
function pick(value, allowed, fallback) {
  return allowed.includes(value) ? value : fallback;
}

export function loadPreferences() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "{}") ?? {};
    return {
      period: pick(saved.period, PERIOD_CHOICES, DEFAULT_PREFERENCES.period),
      inactiveDays: pick(saved.inactiveDays, INACTIVE_DAY_CHOICES, DEFAULT_PREFERENCES.inactiveDays),
      pageSize: pick(saved.pageSize, PAGE_SIZE_CHOICES, DEFAULT_PREFERENCES.pageSize),
    };
  } catch {
    return { ...DEFAULT_PREFERENCES };
  }
}

export function savePreferences(preferences) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences));
  } catch {
    // Browser storage can be blocked. The app still works, the choice just won't be remembered.
  }
}