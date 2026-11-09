import { useState } from "react";
import { api } from "../api/client.js";
import PageHeader from "../components/PageHeader.jsx";
import Panel from "../components/Panel.jsx";
import RequireRepo from "../components/RequireRepo.jsx";
import StatCard from "../components/StatCard.jsx";
import { useRepo } from "../context/RepoContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { formatDate, formatNumber } from "../utils/format.js";

const THRESHOLDS = [14, 30, 60, 90, 180];

function StatusBadge({ branch }) {
  if (branch.flagged_inactive) {
    return (
      <span className="status status-flagged" title="Potentially inactive: worth reviewing">
        inactive
      </span>
    );
  }
  if (branch.status === "inactive") {
    return (
      <span className="status status-quiet" title="Old, but protected (main, master, develop or the current branch), so it is not flagged">
        inactive · protected
      </span>
    );
  }
  return <span className={`status status-${branch.status}`}>{branch.status}</span>;
}

function formatAge(days) {
  if (days === 0) return "today";
  return days === 1 ? "1 day" : `${formatNumber(days)} days`;
}

function BranchesView({ repo }) {
  const [days, setDays] = useState(30);
  const analysis = useApi(() => api.branchAnalysis(repo.path, days), [repo.path, days]);

  const data = analysis.data;
  const summary = data?.summary;
  const pending = analysis.loading && !data;
  const show = (pick) => (summary ? formatNumber(pick(summary)) : pending ? "…" : "—");

  return (
    <>
      <PageHeader title="Branches" description="Local branches only. Nothing is ever deleted or changed.">
        <label className="inline-field">
          <span className="muted">Inactive after</span>
          <select className="input select" value={days} onChange={(event) => setDays(Number(event.target.value))}>
            {THRESHOLDS.map((value) => (
              <option key={value} value={value}>
                {value} days
              </option>
            ))}
          </select>
        </label>
      </PageHeader>

      <div className="stat-grid">
        <StatCard label="Branches" value={show((s) => s.total)} />
        <StatCard label="Active" value={show((s) => s.active)} hint={`under ${days} days old`} />
        <StatCard label="Stale" value={show((s) => s.stale)} hint={`${days} to ${days * 2} days old`} />
        <StatCard label="Flagged inactive" value={show((s) => s.flagged_inactive)} hint={`over ${days * 2} days old`} />
      </div>

      <div style={{ marginTop: 16 }}>
        <Panel
          title="Branch activity"
          note={
            <>
              Branches are flagged only when their last commit is more than {days * 2} days old. <code>main</code>,{" "}
              <code>master</code>, <code>develop</code> and the current branch are never flagged. This tool is
              read-only: to remove a branch yourself, use <code>git branch -d name</code>.
            </>
          }
          error={analysis.error}
          loading={pending}
          empty={data && data.branches.length === 0 && "No branches found."}
        >
          {data && (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Branch</th>
                    <th>Status</th>
                    <th>Last commit</th>
                    <th>Author</th>
                    <th className="num">Age</th>
                    <th className="num" title={`Commits on the branch that are not on ${data.base_branch}`}>
                      Unmerged
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {data.branches.map((branch) => (
                    <tr key={branch.name} className={branch.flagged_inactive ? "row-flagged" : undefined}>
                      <td className="cell-nowrap">
                        <span className="mono">{branch.name}</span>{" "}
                        {branch.is_current && <span className="badge">current</span>}{" "}
                        {branch.is_base && <span className="badge badge-muted">base</span>}
                      </td>
                      <td>
                        <StatusBadge branch={branch} />
                      </td>
                      <td className="cell-nowrap">
                        <span className="hash">{branch.last_commit_hash}</span>{" "}
                        <span className="muted">{formatDate(branch.last_commit_date)}</span>
                      </td>
                      <td className="cell-nowrap">{branch.last_commit_author}</td>
                      <td className="num cell-nowrap">{formatAge(branch.days_since_last_commit)}</td>
                      <td className="num">{branch.is_base ? <span className="muted">—</span> : branch.unmerged_commits}</td>
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

function BranchesContent() {
  const { repo } = useRepo();
  return <BranchesView key={repo.path} repo={repo} />;
}

export default function Branches() {
  return (
    <RequireRepo title="Branches">
      <BranchesContent />
    </RequireRepo>
  );
}