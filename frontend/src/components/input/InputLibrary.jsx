import { Folder, AlertCircle, FolderOpen, X } from "lucide-react";
import InputCard from "./InputCard";
import InputPreviewModal from "./InputPreviewModal";
import SkeletonCard from "../ui/SkeletonCard";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { useInputActions } from "../../hooks/useInputs";

const SKELETON_COUNT = 6;

// Input library: filtered grid + preview/download side effects.
export default function InputLibrary({ inputs, loading, error, onRetry }) {
  const {
    activeInput, previewUrl, previewLoading, previewError,
    openPreview, closePreview, downloadingKey, downloadError,
    clearDownloadError, download,
  } = useInputActions();

  return (
    <section aria-labelledby="inputs-heading">
      <div className="mb-5 flex items-end justify-between">
        <div>
          <h2 id="inputs-heading" className="text-lg font-semibold text-text">Input Library</h2>
          <p className="mt-0.5 text-sm text-muted">Inputs stored in your S3 bucket.</p>
        </div>
        {!loading && !error ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted">
            <Folder size={13} aria-hidden="true" />
            {inputs.length} {inputs.length === 1 ? "input" : "inputs"}
          </span>
        ) : null}
      </div>

      {downloadError ? (
        <div className="mb-4 flex items-center justify-between gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
          <span className="inline-flex items-center gap-2">
            <AlertCircle size={16} className="text-red-500" aria-hidden="true" />
            {downloadError}
          </span>
          <button type="button" onClick={clearDownloadError} aria-label="Dismiss" className="text-red-400 hover:text-red-600">
            <X size={16} />
          </button>
        </div>
      ) : null}

      <Content
        loading={loading}
        error={error}
        inputs={inputs}
        onRetry={onRetry}
        onPreview={openPreview}
        onDownload={download}
        downloadingKey={downloadingKey}
      />

      <InputPreviewModal
        isOpen={Boolean(activeInput)}
        onClose={closePreview}
        input={activeInput}
        url={previewUrl}
        loading={previewLoading}
        error={previewError}
        onDownload={download}
        downloading={downloadingKey === activeInput?.key}
      />
    </section>
  );
}

function Content({ loading, error, inputs, onRetry, onPreview, onDownload, downloadingKey }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: SKELETON_COUNT }).map((_, i) => <SkeletonCard key={i} />)}
      </div>
    );
  }

  if (error) {
    return (
      <Card className="flex flex-col items-center px-6 py-12 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-red-50 text-red-500">
          <AlertCircle size={22} aria-hidden="true" />
        </span>
        <h3 className="mt-4 text-sm font-semibold text-text">Couldn&apos;t load inputs</h3>
        <p className="mt-1 max-w-sm text-sm text-muted">{error}</p>
        <Button variant="secondary" size="md" className="mt-5" onClick={onRetry}>Try again</Button>
      </Card>
    );
  }

  if (inputs.length === 0) {
    return (
      <Card className="flex flex-col items-center px-6 py-12 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <FolderOpen size={22} aria-hidden="true" />
        </span>
        <h3 className="mt-4 text-sm font-semibold text-text">No inputs yet</h3>
        <p className="mt-1 max-w-sm text-sm text-muted">Uploaded inputs will appear here.</p>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {inputs.map((item) => (
        <InputCard
          key={item.key}
          input={item}
          onPreview={onPreview}
          onDownload={onDownload}
          downloading={downloadingKey === item.key}
        />
      ))}
    </div>
  );
}
