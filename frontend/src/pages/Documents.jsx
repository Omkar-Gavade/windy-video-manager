import Container from "../components/ui/Container";
import FilterBar from "../components/FilterBar";
import DocumentUpload from "../components/document/DocumentUpload";
import DocumentLibrary from "../components/document/DocumentLibrary";
import { useDocuments } from "../hooks/useDocuments";

// Document Manager page (route "/documents"). Same composition pattern as
// VideoDashboard, same design language (Container, Card-based sections,
// shared FilterBar) — a separate page, not mixed with videos.
export default function Documents() {
  const { documents, loading, error, refetch } = useDocuments();

  const handleLoad = (filters) =>
    refetch({ state: filters.state, plant: filters.plant, documentDate: filters.recordingDate });

  return (
    <Container className="space-y-8">
      <FilterBar
        onLoad={handleLoad}
        loading={loading}
        dateLabel="Document Date"
        buttonLabel="Load Documents"
      />
      <DocumentUpload onUploaded={refetch} />
      <DocumentLibrary
        documents={documents}
        loading={loading}
        error={error}
        onRetry={refetch}
      />
    </Container>
  );
}
