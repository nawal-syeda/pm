import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const executablePath = process.env.PLAYWRIGHT_EXECUTABLE_PATH;
const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL;
const staticDirectory = path.resolve(process.cwd(), "out");

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
        command:
          "npm run build && uv run --project ../backend uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 3000",
        env: {
          ...process.env,
          PM_STATIC_DIR: staticDirectory,
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
