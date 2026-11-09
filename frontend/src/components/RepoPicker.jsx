import { useState } from "react";
import { AlertTriangle, FolderOpen } from "lucide-react";
import { useRepo } from "../context/RepoContext.jsx";
import { formatRelativeTime } from "../utils/format.js";

export default function RepoPicker() {
  const { openRepo, recent, loading, error } = useRepo();
  const [path, setPath] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    if (path.trim()) openRepo(path);
  }

  return (
    <div>
      <form onSubmit={handleSubmit}>
        <label htmlFor="repo-path" className="field-label">
          Repository path
        </label>
        <div className="picker-row">
          <input
            id="repo-path"
            className="input mono"
            type="text"
            value={path}
            onChange={(event) => setPath(event.target.value)}
            placeholder="C:\path\to\repository"
            spellCheck={false}
            autoComplete="off"
          />
          <button className="btn btn-primary" type="submit" disabled={loading || !path.trim()}>
            <FolderOpen size={16} />
            {loading ? "Opening…" : "Open"}
          </button>
        </div>
        <p className="hint">
          Use the folder that directly contains the <code>.git</code> directory. In File Explorer,
          right-click the folder and choose “Copy as path”, then paste it here.
        </p>
      </form>

      {error && (
        <p className="alert alert-error" role="alert">
          <AlertTriangle size={16} />
          <span>{error}</span>
        </p>
      )}

      {recent.length > 0 && (
        <div className="recent">
          <h3 className="section-label">Recent</h3>
          <ul className="recent-list">
            {recent.map((item) => (
              <li key={item.path}>
                <button
                  type="button"
                  className="recent-item"
                  onClick={() => openRepo(item.path)}
                  disabled={loading}
                >
                  <span className="recent-name">{item.name}</span>
                  <span className="recent-path mono">{item.path}</span>
                  <span className="recent-time">{formatRelativeTime(item.last_opened_at)}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}