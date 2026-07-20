import { useCallback, useState } from "react";
import Container from "../components/ui/Container";
import InputFilterBar from "../components/input/InputFilterBar";
import InputUpload from "../components/input/InputUpload";
import InputLibrary from "../components/input/InputLibrary";
import { useInputs } from "../hooks/useInputs";

// Input Manager page (route "/inputs"). Search-first: nothing is fetched until
// the user picks State + Plant + Input Date and presses Load.
// Layout order: filters -> results -> upload.
export default function Inputs() {
  const { inputs, loading, error, loaded, refetch } = useInputs();
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
      <InputFilterBar onLoad={handleLoad} loading={loading} />
      <InputLibrary
        inputs={inputs}
        loading={loading}
        error={error}
        loaded={loaded}
        onRetry={refresh}
      />
      <InputUpload onUploaded={refresh} />
    </Container>
  );
}
