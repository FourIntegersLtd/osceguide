import { defineConfig } from "@playwright/test";

/**
 * End-to-end journeys (docs/CORE-JOURNEYS.md), run against a LOCAL platform-api.
 *
 *   npm run e2e          both arms
 *   npm run e2e:train    the consumer journeys
 *   npm run e2e:assess   the institution journeys
 *
 * Needs platform-api on :8002 (migrated and seeded, see docs/CORE-JOURNEYS.md).
 * The web server is started here on :3101 in its own build folder, with its
 * /api/v1 proxy pinned to the local api, so it never disturbs `npm run dev`
 * on :3100. e2e/global-setup.ts refuses to run when the api is not on localhost.
 */
const API = process.env.VERIFY_API_URL ?? "http://127.0.0.1:8002";
const WEB = process.env.VERIFY_WEB_URL ?? "http://localhost:3101";
// The verify harness reads these when e2e/support imports it.
process.env.VERIFY_API_URL = API;
process.env.VERIFY_WEB_URL = WEB;

export default defineConfig({
  testDir: "./e2e",
  globalSetup: "./e2e/global-setup.ts",
  // One shared world per run, and the api rate-limits sign-ins: run serially.
  workers: 1,
  fullyParallel: false,
  retries: 0,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  reporter: [["list"]],
  outputDir: "test-results",
  use: {
    baseURL: WEB,
    // System Chrome, as the verify harness uses; no browser download needed.
    channel: "chrome",
    // A fake microphone, as the verify harness launches: the practice screens stop at "allow your microphone" without one.
    launchOptions: { args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] },
    permissions: ["microphone"],
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    actionTimeout: 20_000,
    navigationTimeout: 90_000,
  },
  webServer: {
    command: "npx next dev --port 3101 --turbopack",
    url: `${WEB}/login`,
    // Only ever reuse a server you started yourself on :3101 with PLATFORM_API_URL pointing at the local api.
    reuseExistingServer: Boolean(process.env.E2E_REUSE_SERVER),
    timeout: 180_000,
    env: { PLATFORM_API_URL: API, NEXT_DIST_DIR: ".next-e2e" },
  },
});
