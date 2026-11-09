export default function ScoreBadge({ quality }) {
  if (quality.exempt) {
    return (
      <span className="score score-exempt" title={quality.exempt_reason}>
        auto
      </span>
    );
  }
  return (
    <span className={`score score-${quality.rating}`} title={quality.rating}>
      {quality.score}
    </span>
  );
}