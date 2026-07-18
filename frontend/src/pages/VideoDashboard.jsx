import Container from "../components/ui/Container";
import FilterBar from "../components/FilterBar";
import UploadCard from "../components/UploadCard";
import VideoLibrary from "../components/VideoLibrary";
import { useVideos } from "../hooks/useVideos";

// Video page (route "/"). Unchanged behaviour — only relocated out of App.jsx
// so App can route between this and the Inputs page.
// The filter bar drives fetching (on Load Videos); the upload card carries its
// own metadata; the library renders whatever the backend returns.
export default function VideoDashboard() {
  const { videos, loading, error, refetch } = useVideos();

  return (
    <Container className="space-y-8">
      <FilterBar onLoad={refetch} loading={loading} />
      <UploadCard onUploaded={refetch} />
      <VideoLibrary videos={videos} loading={loading} error={error} onRetry={refetch} />
    </Container>
  );
}
