import { useCallback, useState } from "react";
import { listVideos } from "../services/videoApi";

// Encapsulates the library's data lifecycle: fetching, loading, and errors.
// Nothing is fetched on mount — the list API runs only when `refetch` is
// called with explicit filters (the Load button). `loaded` distinguishes
// "nothing searched yet" from "searched, no results".
// Returns { videos, loading, error, loaded, refetch }.
export function useVideos() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loaded, setLoaded] = useState(false);

  const refetch = useCallback((filters = {}) => {
    setLoading(true);
    setError(null);

    return listVideos(filters)
      .then((data) => {
        setVideos(data || []);
        setLoaded(true);
        setLoading(false);
      })
      .catch((err) => {
        if (err?.code === "ERR_CANCELED" || err?.name === "CanceledError") return;
        setError(err.message);
        setLoaded(true);
        setLoading(false);
      });
  }, []);

  return { videos, loading, error, loaded, refetch };
}
