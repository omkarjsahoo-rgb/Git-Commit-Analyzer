import PageHeader from "../components/PageHeader.jsx";
import RequireRepo from "../components/RequireRepo.jsx";
import StatCard from "../components/StatCard.jsx";
import { useRepo } from "../context/RepoContext.jsx";
import { formatNumber } from "../utils/format.js";

function OverviewContent() {
  const { repo } = useRepo();

  return (
    <>
      <PageHeader title="Overview" description={repo.path} />
      <div className="stat-grid">
        <StatCard label="Total commits" value={formatNumber(repo.total_commits)} />
        <StatCard label="Branches" value={formatNumber(repo.branch_count)} />
        <StatCard label="Current branch" value={repo.current_branch ?? "detached HEAD"} mono />
      </div>
      {!repo.has_commits && (
        <section className="card" style={{ marginTop: 16 }}>
          <p className="muted">This repository has no commits yet, so there is nothing to analyze.</p>
        </section>
      )}
    </>
  );
}

export default function Overview() {
  return (
    <RequireRepo title="Overview">
      <OverviewContent />
    </RequireRepo>
  );
}