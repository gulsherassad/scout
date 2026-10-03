import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend's CORS allows this port only (scout.api.FRONTEND_ORIGINS)
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
  preview: { port: 5173, strictPort: true },
});
