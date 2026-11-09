import { formatDate } from "../utils/format.js";
import ScoreBadge from "./ScoreBadge.jsx";

export default function RecentCommitsTable({ commits }) {
  return (
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
          {commits.map((commit) => (
            <tr key={commit.hash}>
              <td>
                <span className="hash">{commit.short_hash}</span>
              </td>
              <td className="cell-subject" title={commit.subject}>
                {commit.subject || "(no message)"}
              </td>
              <td className="cell-nowrap">{commit.author_name}</td>
              <td className="cell-nowrap muted">{formatDate(commit.committed_at)}</td>
              <td className="num">
                <ScoreBadge quality={commit.quality} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}