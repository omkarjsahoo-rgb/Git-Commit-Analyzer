import { Fragment, useState } from "react";
import { ChevronDown, ChevronRight, Search } from "lucide-react";
import { api } from "../api/client.js";
import CommitDetail from "../components/CommitDetail.jsx";
import PageHeader from "../components/PageHeader.jsx";
import Pagination from "../components/Pagination.jsx";
import Panel from "../components/Panel.jsx";
import RequireRepo from "../components/RequireRepo.jsx";
import ScoreBadge from "../components/ScoreBadge.jsx";
import { useRepo } from "../context/RepoContext.jsx";
import { useApi } from "../hooks/useApi.js";
import { useDebounce } from "../hooks/useDebounce.js";
import { formatDate, formatNumber } from "../utils/format.js";
import { loadPreferences } from "../utils/preferences.js";

const RATING_OPTIONS = [
  { value: "", label: "All ratings" },
  { value: "excellent", label: "Excellent (80+)" },
  { value: "good", label: "Good (60–79)" },
  { value: "fair", label: "Fair (40–59)" },
  { value: "poor", label: "Poor (under 40)" },
  { value: "exempt", label: "Auto-generated" },
];

function CommitsView({ repo }) {
  const [search, setSearch] = useState("");
  const [rating, setRating] = useState("");
  const [branch, setBranch] = useState("");
  const [page, setPage] = useState(0);
  const [expanded, setExpanded] = useState(null);
  const [pageSize] = useState(() => loadPreferences().pageSize);

  const debouncedSearch = useDebounce(search, 300);

  const branches = useApi(() => api.branches(repo.path), [repo.path]);
  const commits = useApi(
    () =>
      api.commits(repo.path, {
        limit: pageSize,
        offset: page * pageSize,
        branch,
        q: debouncedSearch.trim(),
        rating,
      }),
    [repo.path, page, branch, rating, debouncedSearch],
  );

  const data = commits.data;
  const filtering = Boolean(search.trim() || rating || branch);

  // Any filter change goes back to page 1 and closes the open row.
  function changeFilter(setter) {
    return (event) => {
      setter(event.target.value);
      setPage(0);
      setExpanded(null);
    };
  }

  function changePage(next) {
    setPage(next);
    setExpanded(null);
  }

  return (
    <>
      <PageHeader title="Commits" description="Complete commit history and message quality." />

      <div className="toolbar">
        <div className="search">
          <Search size={14} />
          <input
            className="input"
            type="search"
            value={search}
            onChange={changeFilter(setSearch)}
            placeholder="Search message, author or hash"
            aria-label="Search commits"
            spellCheck={false}
          />
        </div>

        <select className="input select" value={rating} onChange={changeFilter(setRating)} aria-label="Filter by quality">
          {RATING_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <select className="input select" value={branch} onChange={changeFilter(setBranch)} aria-label="Filter by branch">
          <option value="">All branches</option>
          {branches.data?.branches.map((item) => (
            <option key={item.name} value={item.name}>
              {item.name}
            </option>
          ))}
        </select>
      </div>

      <Panel
        title="Commit history"
        actions={data && <span className="muted">{formatNumber(data.total)} commits</span>}
        error={commits.error}
        loading={commits.loading && !data}
        empty={data && data.commits.length === 0 && (filtering ? "No commits match these filters." : "No commits found.")}
      >
        {data && (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Hash</th>
                    <th>Message</th>
                    <th>Author</th>
                    <th>Date</th>
                    <th className="num">Quality</th>
                  </tr>
                </thead>
                <tbody>
                  {data.commits.map((commit) => {
                    const open = expanded === commit.hash;
                    const Icon = open ? ChevronDown : ChevronRight;
                    return (
                      <Fragment key={commit.hash}>
                        <tr>
                          <td>
                            <span className="hash">{commit.short_hash}</span>
                          </td>
                          <td className="cell-subject">
                            <button
                              type="button"
                              className="row-toggle"
                              aria-expanded={open}
                              title={commit.subject}
                              onClick={() => setExpanded(open ? null : commit.hash)}
                            >
                              <Icon size={14} />
                              <span>{commit.subject || "(no message)"}</span>
                            </button>
                          </td>
                          <td className="cell-nowrap">{commit.author_name}</td>
                          <td className="cell-nowrap muted">{formatDate(commit.committed_at)}</td>
                          <td className="num">
                            <ScoreBadge quality={commit.quality} />
                          </td>
                        </tr>
                        {open && (
                          <tr className="detail-row">
                            <td colSpan={5}>
                              <CommitDetail commit={commit} />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <Pagination page={page} pageSize={pageSize} total={data.total} onChange={changePage} />
            {data.truncated && (
              <p className="panel-note">Search and quality filters cover the newest 5,000 commits only.</p>
            )}
          </>
        )}
      </Panel>
    </>
  );
}

function CommitsContent() {
  const { repo } = useRepo();
  return <CommitsView key={repo.path} repo={repo} />;
}

export default function Commits() {
  return (
    <RequireRepo title="Commits">
      <CommitsContent />
    </RequireRepo>
  );
}