import { Download, AlertCircle, Loader2, FileX2 } from "lucide-react";
import Modal from "../ui/Modal";
import Button from "../ui/Button";

function isPdf(filename = "") {
  return filename.toLowerCase().endsWith(".pdf");
}

// Document preview modal. PDFs render inline via an iframe (browsers have a
// native PDF viewer); every other supported format shows a "Preview not
// available" fallback with Download still offered.
export default function DocumentPreviewModal({
  isOpen,
  onClose,
  document: doc,
  url,
  loading,
  error,
  onDownload,
  downloading = false,
}) {
  const pdf = isPdf(doc?.filename);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={doc?.filename || "Preview"}
      footer={
        <>
          <Button variant="secondary" size="md" onClick={onClose}>
            Close
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={() => onDownload(doc)}
            disabled={downloading}
          >
            {downloading ? (
              <Loader2 size={16} className="animate-spin" aria-hidden="true" />
            ) : (
              <Download size={16} aria-hidden="true" />
            )}
            Download
          </Button>
        </>
      }
    >
      <div className="flex h-[65vh] w-full items-center justify-center overflow-hidden rounded-xl bg-canvas">
        {loading ? (
          <Loader2 size={28} className="animate-spin text-muted" aria-hidden="true" />
        ) : error ? (
          <div className="flex flex-col items-center gap-2 px-6 text-center text-muted">
            <AlertCircle size={24} aria-hidden="true" />
            <p className="text-sm">{error}</p>
          </div>
        ) : url && pdf ? (
          <iframe src={url} title={doc?.filename} className="h-full w-full border-0" />
        ) : url ? (
          <div className="flex flex-col items-center gap-2 px-6 text-center text-muted">
            <FileX2 size={28} aria-hidden="true" />
            <p className="text-sm">Preview not available.</p>
            <p className="text-xs">Use Download to open this file.</p>
          </div>
        ) : null}
      </div>
    </Modal>
  );
}
