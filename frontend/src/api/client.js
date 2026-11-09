const BACKEND_DOWN =
  "Cannot reach the backend. Check that `python run.py` is running (port 5001).";

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// One place that sends requests and turns every failure into a readable ApiError.
async function request(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new ApiError(BACKEND_DOWN);
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    // The body was not JSON (for example, the dev proxy could not reach Flask).
  }

  if (!response.ok) {
    const message =
      data?.error ||
      (response.status >= 500 ? BACKEND_DOWN : `Request failed (${response.status}).`);
    throw new ApiError(message, response.status);
  }
  return data;
}

function get(endpoint, params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, value);
    }
  }
  const text = query.toString();
  return request(text ? `${endpoint}?${text}` : endpoint);
}

export const api = {
  health: () => get("/api/health"),

  openRepository: (path) =>
    request("/api/repository/open", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path }),
    }),
  recentRepositories: () => get("/api/repository/recent"),

  // Used from step 5B onward.
  commits: (path, options) => get("/api/commits", { path, ...options }),
  branches: (path) => get("/api/branches", { path }),
  qualitySummary: (path, options) => get("/api/quality/summary", { path, ...options }),
  contributors: (path, options) => get("/api/contributors", { path, ...options }),
  activity: (path, period, options) => get("/api/activity", { path, period, ...options }),
  branchAnalysis: (path, inactiveDays) =>
    get("/api/branches/analysis", { path, inactive_days: inactiveDays }),
};