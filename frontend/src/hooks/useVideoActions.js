import { useCallback, useState } from "react";
import { getPreviewUrl, getDownloadUrl } from "../services/videoApi";

// Trigger a browser download for a presigned URL. The S3 response carries
// Content-Disposition: attachment, so the file saves rather than navigating.
function triggerDownload(url) {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

// Encapsulates the preview (modal) and download side effects for a video.
export function useVideoActions() {
  const [activeVideo, setActiveVideo] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);

  const [downloadingKey, setDownloadingKey] = useState(null);
  const [downloadError, setDownloadError] = useState(null);

  const openPreview = useCallback((video) => {
    setActiveVideo(video);
    setPreviewUrl(null);
    setPreviewError(null);
    setPreviewLoading(true);

    getPreviewUrl(video.key)
      .then((data) => setPreviewUrl(data.url))
      .catch((err) => setPreviewError(err.message))
      .finally(() => setPreviewLoading(false));
  }, []);

  const closePreview = useCallback(() => {
    setActiveVideo(null);
    setPreviewUrl(null);
    setPreviewError(null);
  }, []);

  const download = useCallback((video) => {
    setDownloadError(null);
    setDownloadingKey(video.key);

    getDownloadUrl(video.key)
      .then((data) => triggerDownload(data.url))
      .catch((err) => setDownloadError(err.message))
      .finally(() => setDownloadingKey(null));
  }, []);

  return {
    activeVideo,
    previewUrl,
    previewLoading,
    previewError,
    openPreview,
    closePreview,
    downloadingKey,
    downloadError,
    clearDownloadError: () => setDownloadError(null),
    download,
  };
}
