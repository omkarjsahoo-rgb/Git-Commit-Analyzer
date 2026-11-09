import { FolderGit2, GitBranch, Menu } from "lucide-react";
import { useRepo } from "../context/RepoContext.jsx";
import { formatNumber } from "../utils/format.js";

export default function TopBar({ onMenu }) {
  const { repo, restoring } = useRepo();

  return (
    <header className="topbar">
      <button type="button" className="icon-btn menu-btn" onClick={onMenu} aria-label="Open navigation">
        <Menu size={18} />
      </button>

      <div className="repo-chip">
        <FolderGit2 size={16} className="repo-chip-icon" />
        {repo ? (
          <>
            <span className="repo-chip-name">{repo.name}</span>
            <span className="badge mono">
              <GitBranch size={12} />
              {repo.current_branch ?? "detached HEAD"}
            </span>
            <span className="repo-chip-meta">{formatNumber(repo.total_commits)} commits</span>
          </>
        ) : (
          <span className="muted">{restoring ? "Reopening last repository…" : "No repository open"}</span>
        )}
      </div>
    </header>
  );
}