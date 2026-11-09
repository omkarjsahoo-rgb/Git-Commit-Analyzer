import { ChevronLeft, ChevronRight } from "lucide-react";
import { formatNumber } from "../utils/format.js";

// `page` starts at 0. The parent owns the page number; this only draws buttons.
export default function Pagination({ page, pageSize, total, onChange }) {
  if (total === 0) return null;

  const from = page * pageSize + 1;
  const to = Math.min(total, (page + 1) * pageSize);
  const lastPage = Math.ceil(total / pageSize) - 1;

  return (
    <div className="pagination">
      <span className="muted">
        {formatNumber(from)}–{formatNumber(to)} of {formatNumber(total)}
      </span>
      <div className="pagination-controls">
        <button type="button" className="btn btn-sm" disabled={page === 0} onClick={() => onChange(page - 1)}>
          <ChevronLeft size={14} />
          Previous
        </button>
        <span className="muted">
          Page {page + 1} of {lastPage + 1}
        </span>
        <button type="button" className="btn btn-sm" disabled={page >= lastPage} onClick={() => onChange(page + 1)}>
          Next
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}