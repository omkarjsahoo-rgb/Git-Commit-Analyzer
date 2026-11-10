import { useState } from "react";
import { api } from "../api/client.js";
import ActivityChart from "../components/charts/ActivityChart.jsx";
import ContributorChart from "../components/charts/ContributorChart.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Panel from "../components/Panel.jsx";
import PeriodToggle from "../components/PeriodToggle.jsx";
import RequireRepo from "../components/RequireRepo.jsx";
import StatCard from "../components/StatCard.jsx";
import { useRepo } from "../context/RepoContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { formatDate, formatNumber, ratingFor } from "../utils/format.js";
import { loadPreferences } from "../utils/preferences.js";

function ContributorsView({ repo }) {
  const [period, setPeriod] = useState(() => loadPreferences().period);

  const contributors = useApi(() => api.contributors(repo.path), [repo.path]);
  const activity = useApi(() => api.activity(repo.path, period), [repo.path, period]);

  const data = contributors.data;
  const list = data?.contributors ?? [];
  const top = list[0];
  const activityData = activity.data;
  const pending = contributors.loading && !data;

  return (
    <>
      <PageHeader title="Contributors" description="Individual contributor analytics." />

      <div className="stat-grid">
        <StatCard label="Contributors" value={data ? formatNumber(data.contributor_count) : pending ? "…" : "—"} />
        <StatCard
          label="Most active"
          value={top ? top.name : pending ? "…" : "—"}
          hint={top ? `${formatNumber(top.commits)} commits · ${top.percent}%` : undefined}
        />
        <StatCard
          label="Commits analyzed"
          value={data ? formatNumber(data.analyzed) : pending ? "…" : "—"}
          hint={data?.truncated ? `newest of ${formatNumber(data.total_commits)} total` : undefined}
        />
      </div>

      <div className="dash-grid">
        <Panel
          title="Commits per contributor"
          note={list.length > 8 ? `Top 8 of ${list.length} contributors. The table below lists everyone.` : null}
          error={contributors.error}
          loading={pending}
          empty={data && list.length === 0 && "No contributors found."}
        >
          {data && <ContributorChart contributors={list} />}
        </Panel>

        <Panel
          title="Active contributors over time"
          actions={<PeriodToggle value={period} onChange={setPeriod} />}
          note={activityData?.range_start ? `${activityData.range_start} to ${activityData.range_end}` : null}
          error={activity.error}
          loading={activity.loading && !activityData}
          empty={activityData && activityData.labels.length === 0 && "No commits to chart."}
        >
          {activityData && (
            <ActivityChart
              labels={activityData.labels}
              commits={activityData.active_contributors}
              label="Active contributors"
            />
          )}
        </Panel>

        <Panel
          className="span-2"
          title="All contributors"
          note="People are matched by email address, so one person using several name spellings counts once. Quality averages skip merge and other auto-generated commits."
          error={contributors.error}
          loading={pending}
          empty={data && list.length === 0 && "No contributors found."}
        >
          {data && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Contributor</th>
                    <th className="num">Commits</th>
                    <th>Share</th>
                    <th className="num">Active days</th>
                    <th>First commit</th>
                    <th>Last commit</th>
                    <th className="num">Avg quality</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map((person) => (
                    <tr key={person.email || person.name}>
                      <td className="cell-nowrap">
                        <div>{person.name}</div>
                        <div className="muted small mono">{person.email || "no email"}</div>
                      </td>
                      <td className="num">{formatNumber(person.commits)}</td>
                      <td>
                        <div className="share">
                          <div className="share-bar">
                            <span style={{ width: `${person.percent}%` }} />
                          </div>
                          <span className="share-pct mono">{person.percent}%</span>
                        </div>
                      </td>
                      <td className="num">{formatNumber(person.active_days)}</td>
                      <td className="cell-nowrap muted">{formatDate(person.first_commit_at)}</td>
                      <td className="cell-nowrap muted">{formatDate(person.last_commit_at)}</td>
                      <td className="num">
                        {person.average_quality === null ? (
                          <span className="muted">—</span>
                        ) : (
                          <span
                            className={`score score-${ratingFor(person.average_quality)}`}
                            title={`Average of ${person.scored_commits} scored commits`}
                          >
                            {person.average_quality}
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

function ContributorsContent() {
  const { repo } = useRepo();
  return <ContributorsView key={repo.path} repo={repo} />;
}

export default function Contributors() {
  return (
    <RequireRepo title="Contributors">
      <ContributorsContent />
    </RequireRepo>
  );
}