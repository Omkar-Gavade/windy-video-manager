import { Download, AlertCircle, Loader2 } from "lucide-react";
import Modal from "./ui/Modal";
import Button from "./ui/Button";

// Video preview modal. Streams the presigned URL via a native HTML5 player.
// Shows a loading state while the URL is being fetched and an error state on
// failure. The Download action reuses the same video.
export default function PreviewModal({
  isOpen,
  onClose,
  video,
  url,
  loading,
  error,
  onDownload,
  downloading = false,
}) {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={video?.filename || "Preview"}
      footer={
        <>
          <Button variant="secondary" size="md" onClick={onClose}>
            Close
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={() => onDownload(video)}
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
      <div className="flex aspect-video w-full items-center justify-center overflow-hidden rounded-xl bg-text/95">
        {loading ? (
          <Loader2 size={28} className="animate-spin text-white/80" aria-hidden="true" />
        ) : error ? (
          <div className="flex flex-col items-center gap-2 px-6 text-center text-white/80">
            <AlertCircle size={24} aria-hidden="true" />
            <p className="text-sm">{error}</p>
          </div>
        ) : url ? (
          <video src={url} controls autoPlay className="h-full w-full">
            Your browser does not support the video tag.
          </video>
        ) : null}
      </div>
    </Modal>
  );
}
