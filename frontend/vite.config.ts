import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { readFileSync } from "fs";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // Local FastAPI. Overridable via .env; never a production host.
  const apiTarget = env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000";
  // The platform version is package.json's, so a release bumps it in one place.
  const { version } = JSON.parse(readFileSync(path.resolve(__dirname, "package.json"), "utf-8"));
  // A release pins its date via .env; any other build reports the day it was built.
  const releaseDate = env.VITE_PLATFORM_RELEASE_DATE || new Date().toISOString().slice(0, 10);

  return {
    server: {
      host: "::",
      port: 8080,
      // Lets the app call the relative /api/v1 default without CORS.
      proxy: {
        "/api/v1": { target: apiTarget, changeOrigin: true },
      },
    },
    define: {
      __PLATFORM_VERSION__: JSON.stringify(version),
      __PLATFORM_RELEASE_DATE__: JSON.stringify(releaseDate),
    },
    plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
