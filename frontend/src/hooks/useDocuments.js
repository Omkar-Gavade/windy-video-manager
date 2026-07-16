import { useCallback, useEffect, useState } from "react";
import {
  listDocuments,
  uploadDocument,
  getPreviewUrl,
  getDownloadUrl,
} from "../services/documentApi";

// Client-side guardrail mirroring the backend's max upload size.
const MAX_UPLOAD_MB = Number(import.meta.env.VITE_MAX_UPLOAD_MB) || 200;

// Allowed document extensions (mirrors the backend allowlist) — used only for
// a friendly client-side check; the backend remains authoritative.
const ALLOWED_EXTENSIONS = [".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".txt"];

function hasAllowedExtension(filename) {
  const lower = filename.toLowerCase();
  return ALLOWED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

// Encapsulates the library's data lifecycle: fetching, loading, and errors.
// Mirrors useVideos. Returns { documents, loading, error, refetch }.
export function useDocuments() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDocuments = useCallback((filters, signal) => {
    setLoading(true);
    setError(null);

    return listDocuments(filters, signal)
      .then((data) => {
        setDocuments(data || []);
        setLoading(false);
      })
      .catch((err) => {
        if (err?.code === "ERR_CANCELED" || err?.name === "CanceledError") return;
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchDocuments({}, controller.signal);
    return () => controller.abort();
  }, [fetchDocuments]);

  const refetch = useCallback((filters = {}) => fetchDocuments(filters), [fetchDocuments]);

  return { documents, loading, error, refetch };
}

// Manages a single upload's lifecycle: validation, progress, success, error.
// Mirrors useUpload. `onSuccess` is invoked after a successful upload.
export function useDocumentUpload(onSuccess) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [uploaded, setUploaded] = useState(null);

  const upload = useCallback(
    (file, metadata) => {
      if (!file) return;

      if (!hasAllowedExtension(file.name)) {
        setError("Unsupported file type. Allowed: PDF, DOC, DOCX, XLS, XLSX, CSV, TXT.");
        setUploaded(null);
        return;
      }
      if (file.size > MAX_UPLOAD_MB * 1024 * 1024) {
        setError(`File exceeds the ${MAX_UPLOAD_MB} MB limit.`);
        setUploaded(null);
        return;
      }

      setError(null);
      setUploaded(null);
      setUploading(true);
      setProgress(0);

      uploadDocument(file, metadata, (event) => {
        if (event.total) {
          setProgress(Math.round((event.loaded / event.total) * 100));
        }
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

// Trigger a browser download for a presigned URL.
function triggerDownload(url) {
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.rel = "noopener";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}

// Encapsulates the preview (modal) and download side effects for a document.
// Mirrors useVideoActions.
export function useDocumentActions() {
  const [activeDocument, setActiveDocument] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState(null);

  const [downloadingKey, setDownloadingKey] = useState(null);
  const [downloadError, setDownloadError] = useState(null);

  const openPreview = useCallback((doc) => {
    setActiveDocument(doc);
    setPreviewUrl(null);
    setPreviewError(null);
    setPreviewLoading(true);

    getPreviewUrl(doc.key)
      .then((data) => setPreviewUrl(data.url))
      .catch((err) => setPreviewError(err.message))
      .finally(() => setPreviewLoading(false));
  }, []);

  const closePreview = useCallback(() => {
    setActiveDocument(null);
    setPreviewUrl(null);
    setPreviewError(null);
  }, []);

  const download = useCallback((doc) => {
    setDownloadError(null);
    setDownloadingKey(doc.key);

    getDownloadUrl(doc.key)
      .then((data) => triggerDownload(data.url))
      .catch((err) => setDownloadError(err.message))
      .finally(() => setDownloadingKey(null));
  }, []);

  return {
    activeDocument,
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
