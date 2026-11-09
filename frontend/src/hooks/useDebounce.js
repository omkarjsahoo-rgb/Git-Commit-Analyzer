import { useEffect, useState } from "react";

// Returns `value` only after it has stopped changing for `delay` ms.
// This stops the search box from sending a request on every single keystroke.
export function useDebounce(value, delay = 300) {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debounced;
}