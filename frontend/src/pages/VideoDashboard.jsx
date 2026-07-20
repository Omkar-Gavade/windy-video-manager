import { useCallback, useState } from "react";
import Container from "../components/ui/Container";
import FilterBar from "../components/FilterBar";
import UploadCard from "../components/UploadCard";
import VideoLibrary from "../components/VideoLibrary";
import { useVideos } from "../hooks/useVideos";

// Video page (route "/"). Search-first: nothing is fetched until the user
// picks State + Plant + Recording Date and presses Load.
// Layout order: filters -> results -> upload.
export default function VideoDashboard() {
  const { videos, loading, error, loaded, refetch } = useVideos();
  // Remember the last search so refreshes (after upload / retry) reuse it
  // instead of falling back to an unfiltered fetch.
  const [filters, setFilters] = useState(null);

  const handleLoad = useCallback(
    (next) => {
      setFilters(next);
      refetch(next);
    },
    [refetch]
  );

  // Only refresh when a search has already been run.
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
      <UploadCard onUploaded={refresh} />
    </Container>
  );
}
