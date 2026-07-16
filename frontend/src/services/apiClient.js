import axios from "axios";

// Single axios instance for the app.
// Base URL comes from the environment; never hardcoded.
const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

// Unwrap the standard success envelope so callers receive `data` directly,
// and normalise errors into a plain Error carrying a user-safe message.
apiClient.interceptors.response.use(
  (response) => response.data?.data,
  (error) => {
    // Let cancellations pass through untouched so hooks can ignore them.
    if (axios.isCancel(error)) {
      return Promise.reject(error);
    }
    const message =
      error.response?.data?.message ||
      "Something went wrong. Please try again.";
    return Promise.reject(new Error(message));
  }
);

export default apiClient;
