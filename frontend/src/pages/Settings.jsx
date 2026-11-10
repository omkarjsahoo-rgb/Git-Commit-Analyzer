import { useState } from "react";
import PageHeader from "../components/PageHeader.jsx";
import RepoPicker from "../components/RepoPicker.jsx";
import { useRepo } from "../context/RepoContext.jsx";
import { formatNumber } from "../utils/format.js";
import {
  DEFAULT_PREFERENCES,
  INACTIVE_DAY_CHOICES,
  PAGE_SIZE_CHOICES,
  PERIOD_CHOICES,
  loadPreferences,
  savePreferences,
} from "../utils/preferences.js";

const PERIOD_LABELS = { daily: "Daily", weekly: "Weekly", monthly: "Monthly" };

export default function Settings() {
  const { repo, closeRepo } = useRepo();
  const [preferences, setPreferences] = useState(loadPreferences);

  function update(key, value) {
    const next = { ...preferences, [key]: value };
    setPreferences(next);
    savePreferences(next);
  }

  function reset() {
    setPreferences({ ...DEFAULT_PREFERENCES });
    savePreferences(DEFAULT_PREFERENCES);
  }

  return (
    <>
      <PageHeader title="Settings" description="Repository configuration and preferences." />
      <section className="card">
        <div className="card-section">
          <h2>Current repository</h2>
          {repo ? (
            <>
              <dl className="details">
                <dt>Name</dt>
                <dd>{repo.name}</dd>
                <dt>Path</dt>
                <dd className="mono">{repo.path}</dd>
                <dt>Branch</dt>
                <dd className="mono">{repo.current_branch ?? "detached HEAD"}</dd>
                <dt>Commits</dt>
                <dd>{formatNumber(repo.total_commits)}</dd>
              </dl>
              <button type="button" className="btn" onClick={closeRepo}>
                Close repository
              </button>
              <p className="hint">Closing only clears the selection in this app. The repository is never modified.</p>
            </>
          ) : (
            <p className="muted" style={{ marginBottom: 0 }}>No repository is open.</p>
          )}
        </div>

        <div className="card-section">
          <h2 style={{ marginBottom: 12 }}>Open a repository</h2>
          <RepoPicker />
        </div>

        <div className="card-section">
          <h2>Preferences</h2>
          <div className="pref-grid">
            <div>
              <label className="field-label" htmlFor="pref-period">
                Default activity period
              </label>
              <select
                id="pref-period"
                className="input select"
                value={preferences.period}
                onChange={(event) => update("period", event.target.value)}
              >
                {PERIOD_CHOICES.map((value) => (
                  <option key={value} value={value}>
                    {PERIOD_LABELS[value]}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="field-label" htmlFor="pref-inactive">
                Branch inactive after
              </label>
              <select
                id="pref-inactive"
                className="input select"
                value={preferences.inactiveDays}
                onChange={(event) => update("inactiveDays", Number(event.target.value))}
              >
                {INACTIVE_DAY_CHOICES.map((value) => (
                  <option key={value} value={value}>
                    {value} days
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="field-label" htmlFor="pref-page-size">
                Commits per page
              </label>
              <select
                id="pref-page-size"
                className="input select"
                value={preferences.pageSize}
                onChange={(event) => update("pageSize", Number(event.target.value))}
              >
                {PAGE_SIZE_CHOICES.map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <button type="button" className="btn" onClick={reset}>
            Reset to defaults
          </button>
          <p className="hint">
            Saved in this browser only. Each page picks up a change the next time you open it. Reports always use the
            30-day branch setting so exports stay comparable.
          </p>
        </div>
      </section>
    </>
  );
}