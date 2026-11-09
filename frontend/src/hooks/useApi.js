import { useEffect, useState } from "react";

// Runs an API call and tracks { data, error, loading }.
// It re-runs whenever the values in `deps` change (for example the repo path or the period).
// While reloading, the old data stays visible so charts don't flash empty.
export function useApi(fetcher, deps) {
  const [state, setState] = useState({ data: null, error: null, loading: true });

  useEffect(() => {
    let cancelled = false;
    setState((previous) => ({ ...previous, loading: true, error: null }));

    fetcher()
      .then((data) => {
        if (!cancelled) setState({ data, error: null, loading: false });
      })
      .catch((err) => {
        if (!cancelled) setState({ data: null, error: err.message, loading: false });
      });

    // If the inputs change before the answer arrives, ignore the stale answer.
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}