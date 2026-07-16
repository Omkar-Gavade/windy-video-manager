import { Folder, AlertCircle, FolderOpen, X } from "lucide-react";
import DocumentCard from "./DocumentCard";
import DocumentPreviewModal from "./DocumentPreviewModal";
import SkeletonCard from "../ui/SkeletonCard";
import Button from "../ui/Button";
import Card from "../ui/Card";
import { useDocumentActions } from "../../hooks/useDocuments";

const SKELETON_COUNT = 6;

// Document library section. Data is supplied by the parent; preview/download
// side effects are owned by useDocumentActions. Simple filtered grid — no
// grouping (unlike the video dashboard).
export default function DocumentLibrary({ documents, loading, error, onRetry }) {
  const {
    activeDocument,
    previewUrl,
    previewLoading,
    previewError,
    openPreview,
    closePreview,
    downloadingKey,
    downloadError,
    clearDownloadError,
    download,
  } = useDocumentActions();

  return (
    <section aria-labelledby="documents-heading">
      <div className="mb-5 flex items-end justify-between">
        <div>
          <h2 id="documents-heading" className="text-lg font-semibold text-text">
            Document Library
          </h2>
          <p className="mt-0.5 text-sm text-muted">Documents stored in your S3 bucket.</p>
        </div>
        {!loading && !error ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1 text-xs font-medium text-muted">
            <Folder size={13} aria-hidden="true" />
            {documents.length} {documents.length === 1 ? "document" : "documents"}
          </span>
        ) : null}
      </div>

      {downloadError ? (
        <div className="mb-4 flex items-center justify-between gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2.5 text-sm text-red-700">
          <span className="inline-flex items-center gap-2">
            <AlertCircle size={16} className="text-red-500" aria-hidden="true" />
            {downloadError}
          </span>
          <button
            type="button"
            onClick={clearDownloadError}
            aria-label="Dismiss"
            className="text-red-400 hover:text-red-600"
          >
            <X size={16} />
          </button>
        </div>
      ) : null}

      <LibraryContent
        loading={loading}
        error={error}
        documents={documents}
        onRetry={onRetry}
        onPreview={openPreview}
        onDownload={download}
        downloadingKey={downloadingKey}
      />

      <DocumentPreviewModal
        isOpen={Boolean(activeDocument)}
        onClose={closePreview}
        document={activeDocument}
        url={previewUrl}
        loading={previewLoading}
        error={previewError}
        onDownload={download}
        downloading={downloadingKey === activeDocument?.key}
      />
    </section>
  );
}

function LibraryContent({
  loading,
  error,
  documents,
  onRetry,
  onPreview,
  onDownload,
  downloadingKey,
}) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: SKELETON_COUNT }).map((_, index) => (
          <SkeletonCard key={index} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card className="flex flex-col items-center px-6 py-12 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-red-50 text-red-500">
          <AlertCircle size={22} aria-hidden="true" />
        </span>
        <h3 className="mt-4 text-sm font-semibold text-text">Couldn&apos;t load documents</h3>
        <p className="mt-1 max-w-sm text-sm text-muted">{error}</p>
        <Button variant="secondary" size="md" className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      </Card>
    );
  }

  if (documents.length === 0) {
    return (
      <Card className="flex flex-col items-center px-6 py-12 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <FolderOpen size={22} aria-hidden="true" />
        </span>
        <h3 className="mt-4 text-sm font-semibold text-text">No documents yet</h3>
        <p className="mt-1 max-w-sm text-sm text-muted">Uploaded documents will appear here.</p>
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {documents.map((doc) => (
        <DocumentCard
          key={doc.key}
          document={doc}
          onPreview={onPreview}
          onDownload={onDownload}
          downloading={downloadingKey === doc.key}
        />
      ))}
    </div>
  );
}
