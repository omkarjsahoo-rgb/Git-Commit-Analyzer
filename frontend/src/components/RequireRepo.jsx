import { useRepo } from "../context/RepoContext.jsx";
import PageHeader from "./PageHeader.jsx";
import RepoPicker from "./RepoPicker.jsx";

// Wrap a page in this. If no repository is open, the page shows the picker instead.
export default function RequireRepo({ title, children }) {
  const { repo, restoring } = useRepo();

  if (repo) return children;
  if (restoring) return <p className="muted">Reopening your last repository…</p>;

  return (
    <>
      <PageHeader title={title} description="Open a local Git repository to see its analysis." />
      <section className="card">
        <RepoPicker />
      </section>
    </>
  );
}