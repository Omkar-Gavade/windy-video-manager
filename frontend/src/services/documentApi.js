import apiClient from "./apiClient";

// API service layer for document operations. Mirrors videoApi.js — each
// function maps to one backend endpoint and returns the unwrapped payload.
// Documents use a completely separate set of endpoints (never reuses the
// video upload endpoint).

/**
 * Fetch documents from the backend, optionally filtered.
 * @param {{state?: string, plant?: string, documentDate?: string}} [filters]
 * @param {AbortSignal} [signal] optional signal to cancel the request
 * @returns {Promise<Array>} list of document items
 */
export function listDocuments(filters = {}, signal) {
  const params = {};
  if (filters.state) params.state = filters.state;
  if (filters.plant) params.plant = filters.plant;
  if (filters.documentDate) params.document_date = filters.documentDate;
  return apiClient.get("/api/documents", { params, signal });
}

/**
 * Upload a single document file to the backend.
 * @param {File} file the document file to upload
 * @param {{state?: string, plant?: string, documentDate?: string, documentTime?: string}} metadata
 * @param {(event: ProgressEvent) => void} [onUploadProgress] progress callback
 * @returns {Promise<Object>} the created document item
 */
export function uploadDocument(file, metadata, onUploadProgress) {
  const form = new FormData();
  form.append("file", file);
  if (metadata?.state) form.append("state", metadata.state);
  if (metadata?.plant) form.append("plant", metadata.plant);
  if (metadata?.documentDate) form.append("document_date", metadata.documentDate);
  if (metadata?.documentTime) form.append("document_time", metadata.documentTime);
  return apiClient.post("/api/documents/upload", form, { onUploadProgress });
}

/**
 * Get a short-lived presigned URL to preview a document inline.
 * @param {string} key the object key
 * @returns {Promise<{url: string}>}
 */
export function getPreviewUrl(key) {
  return apiClient.get("/api/documents/preview", { params: { key } });
}

/**
 * Get a short-lived presigned URL to download the original document file.
 * @param {string} key the object key
 * @returns {Promise<{url: string}>}
 */
export function getDownloadUrl(key) {
  return apiClient.get("/api/documents/download", { params: { key } });
}
