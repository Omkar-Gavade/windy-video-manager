import { useCallback, useState } from "react";
import {
  listInputs,
  uploadInput,
  getPreviewUrl,
  getDownloadUrl,
} from "../services/inputApi";

const MAX_UPLOAD_MB = Number(import.meta.env.VITE_MAX_UPLOAD_MB) || 200;

// Library data lifecycle: fetch, loading, error, filtered refetch.
// Nothing is fetched on mount — the list API runs only when `refetch` is called
// with explicit filters (the Load button). `loaded` distinguishes "nothing
// searched yet" from "searched, no results".
export function useInputs() {
  const [inputs, setInputs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [loaded, setLoaded] = useState(false);

  const refetch = useCallback((filters = {}) => {
    setLoading(true);
    setError(null);
    return listInputs(filters)
      .then((data) => {
        setInputs(data || []);
        setLoaded(true);
        setLoading(false);
      })
      .catch((err) => {
        if (err?.code === "ERR_CANCELED" || err?.name === "CanceledError") return;
        setError(err.message);
        setLoaded(true);
        setLoading(false);
      });
  }, []);

  return { inputs, loading, error, loaded, refetch };
}

// Single upload lifecycle: validation, progress, success, error.
export function useInputUpload(onSuccess) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [uploaded, setUploaded] = useState(null);

  const upload = useCallback(
    (file, metadata) => {
      if (!file) return;
      if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
        setError(`File exceeds the ${MAX_UPLOAD_MB} MB limit.`);
        setUploaded(null);
        return;
      }

      setError(null);
      setUploaded(null);
      setUploading(true);
      setProgress(0);

      uploadInput(file, metadata, (event) => {
        if (event.total) setProgress(Math.round((event.loaded / event.total) * 100));
      })
        .then((result) => {
          setProgress(100);
          setUploading(false);
          setUploaded(result?.filename || file.name);
          onSuccess?.();
        })
        .catch((err) => {
          setUploading(false);
          setError(err.message);
        });
    },
    [onSuccess]
  );

  return { upload, uploading, progress, error, uploaded };
}

function triggerDownload(url) {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

// Preview (modal) + download side effects.
export function useInputActions() {
  const [activeInput, setActiveInput] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);
  const [downloadingKey, setDownloadingKey] = useState(null);
  const [downloadError, setDownloadError] = useState(null);

  const openPreview = useCallback((item) => {
    setActiveInput(item);
    setPreviewUrl(null);
    setPreviewError(null);
    setPreviewLoading(true);
    getPreviewUrl(item.key)
      .then((data) => setPreviewUrl(data.url))
      .catch((err) => setPreviewError(err.message))
      .finally(() => setPreviewLoading(false));
  }, []);

  const closePreview = useCallback(() => {
    setActiveInput(null);
    setPreviewUrl(null);
    setPreviewError(null);
  }, []);

  const download = useCallback((item) => {
    setDownloadError(null);
    setDownloadingKey(item.key);
    getDownloadUrl(item.key)
      .then((data) => triggerDownload(data.url))
      .catch((err) => setDownloadError(err.message))
      .finally(() => setDownloadingKey(null));
  }, []);

  return {
    activeInput,
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
