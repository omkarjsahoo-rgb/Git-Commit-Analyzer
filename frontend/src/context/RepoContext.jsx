import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client.js";

const STORAGE_KEY = "gca.repoPath";
const RepoContext = createContext(null);

function readSavedPath() {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function savePath(path) {
  try {
    if (path) localStorage.setItem(STORAGE_KEY, path);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Browser storage can be blocked. The app still works, it just won't remember the repo.
  }
}

export function RepoProvider({ children }) {
  const [repo, setRepo] = useState(null);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(() => Boolean(readSavedPath()));
  const [error, setError] = useState(null);

  const refreshRecent = useCallback(async () => {
    try {
      const data = await api.recentRepositories();
      setRecent(data.repositories);
    } catch {
      // The recent list is a convenience, so failing to load it is not an error.
    }
  }, []);

  const openRepo = useCallback(
    async (path) => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.openRepository(path);
        setRepo(data.repository);
        savePath(data.repository.path);
        await refreshRecent();
        return true;
      } catch (err) {
        setError(err.message);
        return false;
      } finally {
        setLoading(false);
      }
    },
    [refreshRecent],
  );

  // Only clears the selection inside this app. The repository itself is never touched.
  const closeRepo = useCallback(() => {
    setRepo(null);
    setError(null);
    savePath(null);
  }, []);

  // On first load: reopen the last repository and fetch the recent list.
  useEffect(() => {
    const saved = readSavedPath();
    if (saved) {
      openRepo(saved).finally(() => setRestoring(false));
    }
    refreshRecent();
  }, [openRepo, refreshRecent]);

  const value = useMemo(
    () => ({ repo, recent, loading, restoring, error, openRepo, closeRepo }),
    [repo, recent, loading, restoring, error, openRepo, closeRepo],
  );

  return <RepoContext.Provider value={value}>{children}</RepoContext.Provider>;
}

export function useRepo() {
  const context = useContext(RepoContext);
  if (!context) throw new Error("useRepo must be used inside <RepoProvider>");
  return context;
}