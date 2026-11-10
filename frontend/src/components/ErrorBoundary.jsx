import { Component } from "react";

// If a page throws while rendering, show a message instead of a blank screen.
// React only supports this with a class component.
export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error("Page crashed:", error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;

    return (
      <section className="card">
        <h2>Something went wrong on this page</h2>
        <p className="muted">
          The rest of the app still works. Try again, or open another page. The technical details are in the
          browser console (press F12).
        </p>
        <button type="button" className="btn" onClick={() => this.setState({ error: null })}>
          Try again
        </button>
      </section>
    );
  }
}