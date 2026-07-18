import Container from "../components/ui/Container";
import InputFilterBar from "../components/input/InputFilterBar";
import InputUpload from "../components/input/InputUpload";
import InputLibrary from "../components/input/InputLibrary";
import { useInputs } from "../hooks/useInputs";

// Input Manager page (route "/inputs"). Same composition + design language as
// the Video dashboard; a separate module, not mixed with videos.
export default function Inputs() {
  const { inputs, loading, error, refetch } = useInputs();

  return (
    <Container className="space-y-8">
      <InputFilterBar onLoad={refetch} loading={loading} />
      <InputUpload onUploaded={refetch} />
      <InputLibrary inputs={inputs} loading={loading} error={error} onRetry={refetch} />
    </Container>
  );
}
