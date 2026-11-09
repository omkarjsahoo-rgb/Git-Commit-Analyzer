import { useState } from "react";
import { AlertTriangle, Download, Save } from "lucide-react";
import { api } from "../api/client.js";
import PageHeader from "../components/PageHeader.jsx";
import Panel from "../components/Panel.jsx";
import RequireRepo from "../components/RequireRepo.jsx";
import { useRepo } from "../context/RepoContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { formatDate, formatDateTime, formatNumber, ratingFor } from "../utils/format.js";

const GRADES = {
  healthy: { label: "Healthy", className: "grade-healthy" },
  attention: { label: "Needs attention", className: "grade-attention" },
  at_risk: { label: "At risk", className: "grade-risk" },
  unknown: { label: "Not enough data", className: "grade-unknown" },
};

const EXPORTS = [
  {
    kind: "commits",
    title: "Commit analysis",
    description: "Every commit with its score, rating, issues and suggested subject.",
  },
  {
    kind: "contributors",
    title: "Contributors",
    description: "Commits, share, active days, first and last commit, and average quality per person.",
  },
  {
    kind: "branches",
    title: "Branches",
    description: "Status, age and unmerged commits for each branch (30-day inactivity setting).",
  },
];

function Meter({ component }) {
  const value = component.score;
  return (
    <div className="meter">
      <div className="meter-head">
        <span>
          {component.label} <span className="muted">· weight {component.weight}%</span>
        </span>
        <span className="mono">{value === null ? "—" : `${value}/100`}</span>
      </div>
      <div className="meter-track">
        <div
          className={`meter-fill fill-${value === null ? "none" : ratingFor(value)}`}
          style={{ width: `${value ?? 0}%` }}
        />
      </div>
      <div className="muted small">{component.detail}</div>
    </div>
  );
}

function HealthSummary({ report }) {
  const grade = GRADES[report.health.grade] ?? GRADES.unknown;
  const score = report.health.score;

  return (
    <>
      <div className="health">
        <div>
          <div className="section-label">Health score</div>
          <div className={`health-score ${grade.className}`}>{score ?? "—"}</div>
          <div className={`health-grade ${grade.className}`}>{grade.label}</div>
        </div>
        <div className="meters">
          {report.health.components.map((component) => (
            <Meter key={component.key} component={component} />
          ))}
        </div>
      </div>

      <h3 className="section-label" style={{ marginTop: 24 }}>
        Findings
      </h3>
      <ul className="findings">
        {report.findings.map((finding) => (
          <li key={finding.message}>
            <span className={`dot dot-${finding.level}`} aria-hidden="true" />
            <span className="sr-only">{finding.level}: </span>
            <span>{finding.message}</span>
          </li>
        ))}
      </ul>
    </>
  );
}

function ExportRow({ item, busy, onDownload }) {
  return (
    <li className="export-row">
      <div>
        <div className="export-title">{item.title}</div>
        <div className="muted small">{item.description}</div>
      </div>
      <button type="button" className="btn btn-sm" disabled={busy} onClick={() => onDownload(item.kind)}>
        <Download size={14} />
        {busy ? "Preparing…" : "Download"}
      </button>
    </li>
  );
}

function ReportsView({ repo }) {
  const [busy, setBusy] = useState(null);
  const [downloadError, setDownloadError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  const health = useApi(() => api.reportHealth(repo.path), [repo.path]);
  const snapshots = useApi(() => api.snapshots(repo.path), [repo.path, reloadKey]);
  const report = health.data;

  async function download(kind) {
    setBusy(kind);
    setDownloadError(null);
    try {
      await api.downloadReport(kind, repo.path);
    } catch (err) {
      setDownloadError(err.message);
    } finally {
      setBusy(null);
    }
  }

  async function saveSnapshot() {
    setSaving(true);
    setSaveError(null);
    try {
      await api.saveSnapshot(repo.path);
      setReloadKey((key) => key + 1);
    } catch (err) {
      setSaveError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <PageHeader title="Reports" description="Repository health, detailed commit analysis and CSV exports." />

      {report?.truncated && (
        <p className="hint" style={{ marginTop: 0 }}>
          Based on the newest {formatNumber(report.analyzed)} of {formatNumber(report.total_commits ?? report.metrics.total_commits)} commits.
        </p>
      )}

      <div className="dash-grid" style={{ marginTop: 0 }}>
        <Panel
          className="span-2"
          title="Repository health"
          note="Score = 70% message quality + 30% branch hygiene. Merge commits and other auto-generated messages are not scored."
          error={health.error}
          loading={health.loading && !report}
        >
          {report && <HealthSummary report={report} />}
        </Panel>

        <Panel
          title="Common message problems"
          error={health.error}
          loading={health.loading && !report}
          empty={report && report.issue_breakdown.length === 0 && "No problems found in scored commits."}
        >
          {report && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Problem</th>
                    <th className="num">Commits</th>
                    <th className="num">Share</th>
                  </tr>
                </thead>
                <tbody>
                  {report.issue_breakdown.map((row) => (
                    <tr key={row.code}>
                      <td>{row.label}</td>
                      <td className="num">{formatNumber(row.count)}</td>
                      <td className="num muted">{row.percent}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel title="CSV exports" note="Files open in Excel or any spreadsheet. Text that could run as a formula is neutralized.">
          <ul className="export-list">
            {EXPORTS.map((item) => (
              <ExportRow key={item.kind} item={item} busy={busy === item.kind} onDownload={download} />
            ))}
          </ul>
          {downloadError && (
            <p className="alert alert-error" role="alert" style={{ marginBottom: 0 }}>
              <AlertTriangle size={16} />
              <span>{downloadError}</span>
            </p>
          )}
        </Panel>

        <Panel
          className="span-2"
          title="Lowest-scoring commits"
          note="Fixing these would raise your average the most."
          error={health.error}
          loading={health.loading && !report}
          empty={report && report.lowest_commits.length === 0 && "No scored commits yet."}
        >
          {report && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Hash</th>
                    <th>Message</th>
                    <th>Author</th>
                    <th className="num">Score</th>
                    <th>What to improve</th>
                  </tr>
                </thead>
                <tbody>
                  {report.lowest_commits.map((commit) => (
                    <tr key={commit.hash}>
                      <td>
                        <span className="hash">{commit.short_hash}</span>
                      </td>
                      <td>{commit.subject || "(no message)"}</td>
                      <td className="cell-nowrap">{commit.author_name}</td>
                      <td className="num">
                        <span className={`score score-${commit.rating}`}>{commit.score}</span>
                      </td>
                      <td>
                        <ul className="mini-list">
                          {commit.issues.map((issue) => (
                            <li key={issue}>{issue}</li>
                          ))}
                        </ul>
                        {commit.suggested_subject && (
                          <div className="small">
                            Try: <code>{commit.suggested_subject}</code>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>

        <Panel
          className="span-2"
          title="Analysis history"
          actions={
            <button type="button" className="btn btn-sm" onClick={saveSnapshot} disabled={saving}>
              <Save size={14} />
              {saving ? "Saving…" : "Save snapshot"}
            </button>
          }
          note="Snapshots are stored in this tool's own database, never in your repository. Save one now and again later to compare."
          error={snapshots.error}
          loading={snapshots.loading && !snapshots.data}
          empty={snapshots.data && snapshots.data.snapshots.length === 0 && "No snapshots saved yet."}
        >
          {saveError && (
            <p className="alert alert-error" role="alert" style={{ margin: "0 0 12px" }}>
              <AlertTriangle size={16} />
              <span>{saveError}</span>
            </p>
          )}
          {snapshots.data && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Saved</th>
                    <th className="num">Commits</th>
                    <th className="num">Contributors</th>
                    <th className="num">Branches</th>
                    <th className="num">Quality</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshots.data.snapshots.map((snapshot) => (
                    <tr key={snapshot.id}>
                      <td className="cell-nowrap">{formatDateTime(snapshot.analyzed_at)}</td>
                      <td className="num">{formatNumber(snapshot.total_commits)}</td>
                      <td className="num">{formatNumber(snapshot.contributor_count)}</td>
                      <td className="num">{formatNumber(snapshot.branch_count)}</td>
                      <td className="num">
                        {snapshot.quality_score === null ? (
                          <span className="muted">—</span>
                        ) : (
                          <span className={`score score-${ratingFor(snapshot.quality_score)}`}>
                            {snapshot.quality_score}
                          </span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      </div>
    </>
  );
}

function ReportsContent() {
  const { repo } = useRepo();

  if (!repo.has_commits) {
    return (
      <>
        <PageHeader title="Reports" description={repo.path} />
        <section className="card">
          <p className="muted" style={{ margin: 0 }}>
            This repository has no commits yet, so there is nothing to report on.
          </p>
        </section>
      </>
    );
  }

  return <ReportsView key={repo.path} repo={repo} />;
}

export default function Reports() {
  return (
    <RequireRepo title="Reports">
      <ReportsContent />
    </RequireRepo>
  );
}