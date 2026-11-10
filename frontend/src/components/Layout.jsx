import { useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import ErrorBoundary from "./ErrorBoundary.jsx";
import Sidebar from "./Sidebar.jsx";
import TopBar from "./TopBar.jsx";

export default function Layout() {
  const [navOpen, setNavOpen] = useState(false);
  const location = useLocation();
  const closeNav = () => setNavOpen(false);

  return (
    <div className="app">
      <Sidebar open={navOpen} onClose={closeNav} />
      {navOpen && <div className="scrim" onClick={closeNav} />}

      <div className="main">
        <TopBar onMenu={() => setNavOpen(true)} />
        <main className="content">
          {/* key={pathname}: moving to another page clears a previous crash */}
          <ErrorBoundary key={location.pathname}>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    </div>
  );
}