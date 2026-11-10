import { useState } from "react";
import { api } from "../api/client.js";
import ActivityChart from "../components/charts/ActivityChart.jsx";
import ContributorChart from "../components/charts/ContributorChart.jsx";
import QualityChart from "../components/charts/QualityChart.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Panel from "../components/Panel.jsx";
import RecentCommitsTable from "../components/RecentCommitsTable.jsx";
import RequireRepo from "../components/RequireRepo.jsx";
import StatCard from "../components/StatCard.jsx";
import { useRepo } from "../context/RepoContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { formatNumber } from "../utils/format.js";
import { loadPreferences } from "../utils/preferences.js";

const PERIODS = [
  { id: "daily", label: "Daily" },
  { id: "weekly", label: "Weekly" },
  { id: "monthly", label: "Monthly" },
];

// Shows "…" while loading, "—" if the request failed or there is no value.
function statValue(state, pick) {
  if (state.data) return pick(state.data) ?? "—";
  return state.loading ? "…" : "—";
}

function Dashboard({ repo }) {
   const [period, setPeriod] = useState(() => loadPreferences().period);

  const quality = useApi(() => api.qualitySummary(repo.path), [repo.path]);
  const contributors = useApi(() => api.contributors(repo.path), [repo.path]);
  const activity = useApi(() => api.activity(repo.path, period), [repo.path, period]);
  const recent = useApi(() => api.commits(repo.path, { limit: 10 }), [repo.path]);

  const summary = quality.data?.summary;
  const activityData = activity.data;

  let activityNote = null;
  if (activityData?.range_start) {
    activityNote = `${activityData.range_start} to ${activityData.range_end}`;
    if (activityData.commits_outside_range > 0) {
      activityNote += ` · ${formatNumber(activityData.commits_outside_range)} older commits not shown`;
    }
  }

  const periodToggle = (
    <div className="segmented" role="group" aria-label="Time period">
      {PERIODS.map((item) => (
        <button
          key={item.id}
          type="button"
          className={`segmented-btn${item.id === period ? " is-active" : ""}`}
          aria-pressed={item.id === period}
          onClick={() => setPeriod(item.id)}
        >
          {item.label}
        </button>
      ))}
    </div>
  );

  return (
    <>
      <PageHeader title="Overview" description={repo.path} />

      <div className="stat-grid">
        <StatCard label="Total commits" value={formatNumber(repo.total_commits)} />
        <StatCard
          label="Contributors"
          value={statValue(contributors, (d) => formatNumber(d.contributor_count))}
        />
        <StatCard label="Branches" value={formatNumber(repo.branch_count)} />
        <StatCard
          label="Quality score"
          value={statValue(quality, (d) => d.summary.average_score)}
          hint={summary ? `${summary.scored} scored · ${summary.exempt} auto-generated` : undefined}
        />
        <StatCard
          label="Conventional"
          value={statValue(quality, (d) =>
            d.summary.conventional_percent === null ? null : `${d.summary.conventional_percent}%`,
          )}
          hint={summary ? `${summary.conventional_count} of ${summary.scored} scored commits` : undefined}
        />
      </div>

      {quality.data?.truncated && (
        <p className="hint">
          Quality and contributor figures cover the newest {formatNumber(quality.data.analyzed)} of{" "}
          {formatNumber(quality.data.total)} commits.
        </p>
      )}

      <div className="dash-grid">
        <Panel
          className="span-2"
          title="Commit activity"
          actions={periodToggle}
          note={activityNote}
          error={activity.error}
          loading={activity.loading && !activityData}
          empty={activityData && activityData.labels.length === 0 && "No commits to chart."}
        >
          {activityData && <ActivityChart labels={activityData.labels} commits={activityData.commits} />}
        </Panel>

        <Panel
          title="Top contributors"
          note={
            contributors.data && contributors.data.contributor_count > 8
              ? `Top 8 of ${contributors.data.contributor_count} contributors. See the Contributors page for all.`
              : null
          }
          error={contributors.error}
          loading={contributors.loading && !contributors.data}
          empty={contributors.data && contributors.data.contributors.length === 0 && "No contributors found."}
        >
          {contributors.data && <ContributorChart contributors={contributors.data.contributors} />}
        </Panel>

        <Panel
          title="Message quality"
          note="Merge commits and other auto-generated messages are not scored."
          error={quality.error}
          loading={quality.loading && !quality.data}
          empty={summary && summary.scored === 0 && "No scored commits: every message is auto-generated."}
        >
          {summary && <QualityChart distribution={summary.distribution} />}
        </Panel>

        <Panel
          className="span-2"
          title="Recent commits"
          error={recent.error}
          loading={recent.loading && !recent.data}
          empty={recent.data && recent.data.commits.length === 0 && "No commits found."}
        >
          {recent.data && <RecentCommitsTable commits={recent.data.commits} />}
        </Panel>
      </div>
    </>
  );
}

function OverviewContent() {
  const { repo } = useRepo();

  if (!repo.has_commits) {
    return (
      <>
        <PageHeader title="Overview" description={repo.path} />
        <section className="card">
          <p className="muted" style={{ margin: 0 }}>
            This repository has no commits yet, so there is nothing to analyze.
          </p>
        </section>
      </>
    );
  }

  // key={repo.path}: switching repositories rebuilds the dashboard from scratch.
  return <Dashboard key={repo.path} repo={repo} />;
}

export default function Overview() {
  return (
    <RequireRepo title="Overview">
      <OverviewContent />
    </RequireRepo>
  );
}