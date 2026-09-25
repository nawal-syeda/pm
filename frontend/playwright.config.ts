import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const executablePath = process.env.PLAYWRIGHT_EXECUTABLE_PATH;
const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL;
const staticDirectory = path.resolve(process.cwd(), "out");

// The suite mutates the board (it deletes seeded cards), so it needs a throwaway
// database rather than the dev one. Sharing the dev database made a second run of
// the suite fail on cards the first run had already removed.
//
// Kept out of test-results because Playwright clears that directory at startup,
// and reset inside the server command rather than here: this config module is
// re-evaluated in every worker process, so resetting here would delete the
// database out from under the running server.
const databasePath = path.resolve(process.cwd(), ".e2e-data", "e2e.sqlite3");
const resetDatabase = `node -e "require('fs').rmSync('${databasePath
  .split(path.sep)
  .join("/")}', { force: true })"`;

export default defineConfig({
  testDir: "./tests",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: externalBaseUrl ?? "http://127.0.0.1:3000",
    trace: "retain-on-failure",
  },
  webServer: externalBaseUrl
    ? undefined
    : {
        command: `${resetDatabase} && npm run build && uv run --project ../backend uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 3000`,
        env: {
          ...process.env,
          PM_STATIC_DIR: staticDirectory,
          PM_DATABASE_PATH: databasePath,
        },
        url: "http://127.0.0.1:3000",
        reuseExistingServer: true,
        timeout: 120_000,
      },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        launchOptions: executablePath ? { executablePath } : undefined,
      },
    },
  ],
});
