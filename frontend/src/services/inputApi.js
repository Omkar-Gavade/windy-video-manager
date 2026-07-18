import apiClient from "./apiClient";

// API service layer for input operations. Each function maps 1:1 to a backend
// endpoint under /api/inputs and returns the unwrapped payload.

/**
 * Fetch inputs, optionally filtered.
 * @param {{state?, plant?, inputDate?, category?, wpType?}} [filters]
 * @param {AbortSignal} [signal]
 * @returns {Promise<Array>}
 */
export function listInputs(filters = {}, signal) {
  const params = {};
  if (filters.state) params.state = filters.state;
  if (filters.plant) params.plant = filters.plant;
  if (filters.inputDate) params.input_date = filters.inputDate;
  if (filters.category) params.category = filters.category;
  if (filters.wpType) params.wp_type = filters.wpType;
  return apiClient.get("/api/inputs", { params, signal });
}

/**
 * Upload a single input asset.
 * @param {File} file
 * @param {{state, plant, inputDate?, inputTime, category, wpType?, subCategory?}} metadata
 * @param {(event: ProgressEvent) => void} [onUploadProgress]
 * @returns {Promise<Object>}
 */
export function uploadInput(file, metadata, onUploadProgress) {
  const form = new FormData();
  form.append("file", file);
  if (metadata?.state) form.append("state", metadata.state);
  if (metadata?.plant) form.append("plant", metadata.plant);
  if (metadata?.inputDate) form.append("input_date", metadata.inputDate);
  if (metadata?.inputTime) form.append("input_time", metadata.inputTime);
  if (metadata?.category) form.append("category", metadata.category);
  if (metadata?.wpType) form.append("wp_type", metadata.wpType);
  if (metadata?.subCategory) form.append("sub_category", metadata.subCategory);
  return apiClient.post("/api/inputs/upload", form, { onUploadProgress });
}

/** Dynamic list of States present under the inputs prefix. */
export function getStates(signal) {
  return apiClient.get("/api/inputs/states", { signal });
}

/** Dynamic list of Plants for a given State. */
export function getPlants(state, signal) {
  return apiClient.get("/api/inputs/plants", { params: { state }, signal });
}

/** Text body of a JSON/CSV/TXT input (same-origin, for inline preview). */
export function getContent(key, signal) {
  return apiClient.get("/api/inputs/content", { params: { key }, signal });
}

/** Presigned inline URL for preview. */
export function getPreviewUrl(key) {
  return apiClient.get("/api/inputs/preview", { params: { key } });
}

/** Presigned attachment URL for download. */
export function getDownloadUrl(key) {
  return apiClient.get("/api/inputs/download", { params: { key } });
}
