// PM2 process list for the HMS stack.
//
//   pm2 start ecosystem.config.js     start all three
//   pm2 list                          status, CPU, memory, restarts
//   pm2 logs hms-oss-service          follow one service's logs
//   pm2 restart hms-backend           restart one (e.g. after a .env change)
//   pm2 stop all / pm2 delete all     stop / remove them
//
// Start order matters only for the first request: the backend forwards OSS
// reads to hms-oss-service, and answers 503 for them until it is up.
// Each Python service reads its own .env (backend/.env, oss-service/.env).

const path = require("path");

// Each Python service runs from its own virtualenv.
const venvPython = (dir) =>
  path.join(
    __dirname,
    dir,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );

module.exports = {
  apps: [
    {
      // Read-only OSS microservice: devices, telemetry, alerts from insp_iot.
      name: "hms-oss-service",
      cwd: path.join(__dirname, "oss-service"),
      script: venvPython("oss-service"),
      args: "-m uvicorn app.main:app --host 127.0.0.1 --port 8001",
      interpreter: "none",
      env: { PYTHONPATH: "." },
      autorestart: true,
      max_restarts: 10,
    },
    {
      // HMS backend: authenticates, then serves BSS from MySQL or forwards
      // OSS reads to hms-oss-service.
      name: "hms-backend",
      cwd: path.join(__dirname, "backend"),
      script: venvPython("backend"),
      args: "-m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      interpreter: "none",
      autorestart: true,
      max_restarts: 10,
    },
    {
      // Vite dev server on :8080, proxying /api/v1 to hms-backend.
      name: "hms-frontend",
      cwd: path.join(__dirname, "frontend"),
      script: "node_modules/vite/bin/vite.js",
      interpreter: "node",
      autorestart: true,
      max_restarts: 10,
    },
  ],
};
