import { useCallback, useEffect, useState } from "react";
import { listVideos } from "../services/videoApi";

// Encapsulates the library's data lifecycle: fetching, loading, and errors.
// Returns { videos, loading, error, refetch }.
export function useVideos() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchVideos = useCallback((filters, signal) => {
    setLoading(true);
    setError(null);

    return listVideos(filters, signal)
      .then((data) => {
        setVideos(data || []);
        setLoading(false);
      })
      .catch((err) => {
        // Ignore cancellations from unmount / refetch.
        if (err?.code === "ERR_CANCELED" || err?.name === "CanceledError") return;
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    // Initial load is unfiltered (shows everything, including legacy objects).
    fetchVideos({}, controller.signal);
    return () => controller.abort();
  }, [fetchVideos]);

  const refetch = useCallback((filters = {}) => fetchVideos(filters), [fetchVideos]);

  return { videos, loading, error, refetch };
}
