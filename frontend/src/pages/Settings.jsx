import PageHeader from "../components/PageHeader.jsx";
import RepoPicker from "../components/RepoPicker.jsx";
import { useRepo } from "../context/RepoContext.jsx";
import { formatNumber } from "../utils/format.js";

export default function Settings() {
  const { repo, closeRepo } = useRepo();

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
      </section>
    </>
  );
}