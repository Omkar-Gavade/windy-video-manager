import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite configuration for the React SPA.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
  },
});
