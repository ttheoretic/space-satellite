// Vite: Entwicklungsserver und Build-Werkzeug für das Frontend.
// Im Entwicklungsmodus leitet der Proxy alle /api- und /ws-Anfragen an das
// Python-Backend auf Port 8000 weiter. So sieht der Browser nur eine Adresse.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Recharts ist groß; für eine lokale Anwendung ist ein Bundle von ~500 kB unkritisch.
  build: { chunkSizeWarningLimit: 1000 },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
