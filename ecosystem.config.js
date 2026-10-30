// PM2 process list for the HMS stack.
//
//   pm2 start ecosystem.config.js     start everything
//   pm2 list                          status, CPU, memory, restarts
//   pm2 logs hms-oss-telemetry        follow one service's logs
//   pm2 restart hms-backend           restart one (e.g. after a .env change)
//   pm2 stop all / pm2 delete all     stop / remove them
//
// The OSS side runs as one microservice per domain (device, telemetry, alert,
// energy), all from oss-service/ but each serving only its own routes on its
// own port. The backend forwards each OSS read to the matching service and
// answers 503 for that domain until it is up.
// Each Python service reads its own .env (backend/.env, oss-service/.env);
// the env set here overrides it.

const path = require("path");

// Each Python service runs from its own virtualenv.
const venvPython = (dir) =>
  path.join(
    __dirname,
    dir,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );

// Read-only OSS microservices over insp_iot, one PM2 process each.
const ossServices = [
  { domain: "device", title: "Device", port: 8001 },
  { domain: "telemetry", title: "Telemetry", port: 8002 },
  { domain: "alert", title: "Alert", port: 8003 },
  { domain: "energy", title: "Energy", port: 8004 },
];

const ossApps = ossServices.map(({ domain, title, port }) => ({
  name: `hms-oss-${domain}`,
  cwd: path.join(__dirname, "oss-service"),
  script: venvPython("oss-service"),
  args: `-m uvicorn app.main:app --host 127.0.0.1 --port ${port}`,
  interpreter: "none",
  env: {
    PYTHONPATH: ".",
    APP_NAME: `HMS OSS ${title} Service`,
    OSS_DOMAINS: domain,
  },
  autorestart: true,
  max_restarts: 10,
}));

// Tells the backend which port serves which OSS domain.
const ossUrls = Object.fromEntries(
  ossServices.map(({ domain, port }) => [
    `OSS_${domain.toUpperCase()}_SERVICE_URL`,
    `http://127.0.0.1:${port}`,
  ]),
);

module.exports = {
  apps: [
    ...ossApps,
    {
      // HMS backend: authenticates, then serves BSS from MySQL or forwards
      // OSS reads to the hms-oss-* service for that domain.
      name: "hms-backend",
      cwd: path.join(__dirname, "backend"),
      script: venvPython("backend"),
      args: "-m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      interpreter: "none",
      env: ossUrls,
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
