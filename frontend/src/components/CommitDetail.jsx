import { AlertTriangle } from "lucide-react";
import ScoreBadge from "./ScoreBadge.jsx";

// The expanded panel under a commit row: full message, quality issues and a suggested rewrite.
export default function CommitDetail({ commit }) {
  const { quality } = commit;
  // "Try: ..." duplicates the suggested subject we show separately, so skip it here.
  const hints = quality.suggestions.filter((text) => !text.startsWith("Try:"));

  return (
    <div className="detail">
      <div>
        <div className="section-label">Full message</div>
        <pre className="message-box">{commit.message || "(empty)"}</pre>
      </div>

      <div>
        <div className="section-label">Quality analysis</div>
        {quality.exempt ? (
          <p className="muted" style={{ margin: 0 }}>
            Not scored: {quality.exempt_reason}.
          </p>
        ) : (
          <>
            <p className="detail-line">
              <ScoreBadge quality={quality} />
              <span className="muted">{quality.rating}</span>
              <span>
                {quality.is_conventional
                  ? `Conventional Commits · ${quality.type}${quality.scope ? ` (${quality.scope})` : ""}`
                  : "Not in Conventional Commits format"}
              </span>
            </p>

            {quality.issues.length === 0 ? (
              <p className="muted">No issues found.</p>
            ) : (
              <ul className="issue-list">
                {quality.issues.map((issue) => (
                  <li key={issue.code} className={`issue issue-${issue.severity}`}>
                    <AlertTriangle size={14} />
                    <span>
                      <span className="issue-tag">{issue.severity}</span> {issue.message}
                    </span>
                  </li>
                ))}
              </ul>
            )}

            {quality.suggested_subject && (
              <p>
                Try: <code>{quality.suggested_subject}</code>
              </p>
            )}
            {hints.map((text) => (
              <p key={text} className="hint">
                {text}
              </p>
            ))}
          </>
        )}
      </div>
    </div>
  );
}