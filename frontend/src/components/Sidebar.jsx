import { NavLink } from "react-router-dom";
import {
  FileText,
  GitBranch,
  GitCommitHorizontal,
  LayoutDashboard,
  Settings,
  Users,
  X,
} from "lucide-react";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/commits", label: "Commits", icon: GitCommitHorizontal },
  { to: "/contributors", label: "Contributors", icon: Users },
  { to: "/branches", label: "Branches", icon: GitBranch },
  { to: "/reports", label: "Reports", icon: FileText },
  { to: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar({ open, onClose }) {
  return (
    <aside className={`sidebar${open ? " is-open" : ""}`}>
      <div className="sidebar-brand">
        <GitCommitHorizontal size={18} className="brand-icon" />
        <span>Commit Analyzer</span>
        <button type="button" className="icon-btn sidebar-close" onClick={onClose} aria-label="Close navigation">
          <X size={18} />
        </button>
      </div>

      <nav className="sidebar-nav">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={onClose}
            className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">Read-only · local analysis</div>
    </aside>
  );
}