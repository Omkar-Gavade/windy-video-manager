import { useCallback, useState } from "react";
import Container from "../components/ui/Container";
import FilterBar from "../components/FilterBar";
import VideoLibrary from "../components/VideoLibrary";
import { useVideos } from "../hooks/useVideos";

// Video page (route "/"). Search-first: nothing is fetched until the user
// picks State + Plant + Recording Date and presses Load.
// Layout order: filters -> results.
export default function VideoDashboard() {
  const { videos, loading, error, loaded, refetch } = useVideos();
  // Remember the last search so Retry reuses it instead of falling back to an
  // unfiltered fetch.
  const [filters, setFilters] = useState(null);

  const handleLoad = useCallback(
    (next) => {
      setFilters(next);
      refetch(next);
    },
    [refetch]
  );

  const refresh = useCallback(() => {
    if (filters) refetch(filters);
  }, [filters, refetch]);

  return (
    <Container className="space-y-8">
      <FilterBar onLoad={handleLoad} loading={loading} />
      <VideoLibrary
        videos={videos}
        loading={loading}
        error={error}
        loaded={loaded}
        onRetry={refresh}
      />
    </Container>
  );
}
