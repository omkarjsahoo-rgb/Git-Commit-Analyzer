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

function buildUrl(endpoint, params = {}) {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, value);
    }
  }
  const text = query.toString();
  return text ? `${endpoint}?${text}` : endpoint;
}

function get(endpoint, params) {
  return request(buildUrl(endpoint, params));
}

function post(endpoint, body) {
  return request(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// Fetches a file and hands it to the browser as a download.
// Going through fetch (instead of a plain link) lets us show a readable error if it fails.
async function download(endpoint, params) {
  let response;
  try {
    response = await fetch(buildUrl(endpoint, params));
  } catch {
    throw new ApiError(BACKEND_DOWN);
  }

  if (!response.ok) {
    let message = `Download failed (${response.status}).`;
    try {
      const data = await response.json();
      if (data?.error) message = data.error;
    } catch {
      // Not JSON: keep the generic message.
    }
    throw new ApiError(message, response.status);
  }

  const blob = await response.blob();
  const match = /filename="([^"]+)"/.exec(response.headers.get("Content-Disposition") ?? "");
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = match ? match[1] : "report.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export const api = {
  health: () => get("/api/health"),

  openRepository: (path) => post("/api/repository/open", { path }),
  recentRepositories: () => get("/api/repository/recent"),

  commits: (path, options) => get("/api/commits", { path, ...options }),
  branches: (path) => get("/api/branches", { path }),
  qualitySummary: (path, options) => get("/api/quality/summary", { path, ...options }),
  contributors: (path, options) => get("/api/contributors", { path, ...options }),
  activity: (path, period, options) => get("/api/activity", { path, period, ...options }),
  branchAnalysis: (path, inactiveDays) =>
    get("/api/branches/analysis", { path, inactive_days: inactiveDays }),

  reportHealth: (path) => get("/api/reports/health", { path }),
  snapshots: (path) => get("/api/reports/snapshots", { path }),
  saveSnapshot: (path) => post("/api/reports/snapshots", { path }),
  // kind is "commits", "contributors" or "branches"
  downloadReport: (kind, path) => download(`/api/reports/${kind}.csv`, { path }),
};