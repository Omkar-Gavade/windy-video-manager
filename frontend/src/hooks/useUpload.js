import { useCallback, useState } from "react";
import { uploadVideo } from "../services/videoApi";

// Client-side guardrails mirror the backend so obvious problems are caught
// before a request is sent. The backend remains the authoritative validator.
const MAX_UPLOAD_MB = Number(import.meta.env.VITE_MAX_UPLOAD_MB) || 200;

// Manages a single upload's lifecycle: validation, progress, success, error.
// `onSuccess` is invoked after a successful upload (used to refresh the list).
export function useUpload(onSuccess) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [uploaded, setUploaded] = useState(null); // filename of last success

  const reset = useCallback(() => {
    setUploading(false);
    setProgress(0);
    setError(null);
    setUploaded(null);
  }, []);

  const upload = useCallback(
    (file, metadata) => {
      if (!file) return;

      // Client-side validation.
      if (!file.type.startsWith("video/")) {
        setError("Please select a video file.");
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

      uploadVideo(file, metadata, (event) => {
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

  return { upload, uploading, progress, error, uploaded, reset };
}
