import apiClient from "./apiClient";

// API service layer for video operations. Each function maps to one backend
// endpoint and returns the unwrapped payload.

/**
 * Fetch videos from the backend, optionally filtered.
 * @param {{state?: string, plant?: string, recordingDate?: string}} [filters]
 * @param {AbortSignal} [signal] optional signal to cancel the request
 * @returns {Promise<Array>} list of video items
 */
export function listVideos(filters = {}, signal) {
  const params = {};
  if (filters.state) params.state = filters.state;
  if (filters.plant) params.plant = filters.plant;
  if (filters.recordingDate) params.recording_date = filters.recordingDate;
  return apiClient.get("/api/videos", { params, signal });
}

/**
 * Upload a single video file to the backend.
 * @param {File} file the video file to upload
 * @param {(event: ProgressEvent) => void} [onUploadProgress] progress callback
 * @returns {Promise<Object>} the created video item
 */
export function uploadVideo(file, metadata, onUploadProgress) {
  const form = new FormData();
  form.append("file", file);
  // Metadata — organizes the object under a structured key + JSON sidecar.
  if (metadata?.state) form.append("state", metadata.state);
  if (metadata?.plant) form.append("plant", metadata.plant);
  if (metadata?.recordingDate) form.append("recording_date", metadata.recordingDate);
  if (metadata?.recordingTime) form.append("recording_time", metadata.recordingTime);
  return apiClient.post("/api/videos/upload", form, { onUploadProgress });
}

/** Dynamic list of States present in the bucket. */
export function getStates(signal) {
  return apiClient.get("/api/videos/states", { signal });
}

/** Dynamic list of Plants for a given State. */
export function getPlants(state, signal) {
  return apiClient.get("/api/videos/plants", { params: { state }, signal });
}

/**
 * Get a short-lived presigned URL to stream a video inline.
 * @param {string} key the object key
 * @returns {Promise<{url: string}>}
 */
export function getPreviewUrl(key) {
  return apiClient.get("/api/videos/preview", { params: { key } });
}

/**
 * Get a short-lived presigned URL to download the original file.
 * @param {string} key the object key
 * @returns {Promise<{url: string}>}
 */
export function getDownloadUrl(key) {
  return apiClient.get("/api/videos/download", { params: { key } });
}
