import PageHeader from "./PageHeader.jsx";

export default function PendingPage({ title, description, step }) {
  return (
    <>
      <PageHeader title={title} description={description} />
      <section className="card">
        <p className="muted">This page is built in {step}.</p>
      </section>
    </>
  );
}