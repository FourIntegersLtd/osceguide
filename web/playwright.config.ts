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
// E2E_TARGET=staging runs only the read-only @staging specs against the deployed site
// (promote-*.yml); the accounts come from STAGING_E2E_* (e2e/support/staging.ts).
const STAGING = process.env.E2E_TARGET === "staging";
const env = STAGING
  ? { api: process.env.STAGING_E2E_API_URL ?? "", web: process.env.STAGING_E2E_WEB_URL ?? "" }
  : { api: process.env.VERIFY_API_URL ?? "http://127.0.0.1:8002", web: process.env.VERIFY_WEB_URL ?? "http://localhost:3101" };
const { api: API, web: WEB } = env;
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
  grep: STAGING ? /@staging/ : undefined,
  // The board-*.spec.ts files compare screens with design boards by pixel, for local use
  // (docs/institution-overhaul/verify/board-diff); the core journeys are what CI proves.
  testIgnore: process.env.CI ? /(^|[\\/])board-[^\\/]*\.spec\.ts$/ : undefined,
  reporter: [["list"]],
  outputDir: "test-results",
  use: {
    baseURL: WEB,
    // System Chrome, as the verify harness uses; no browser download needed.
    channel: "chrome",
    // A fake microphone, as the verify harness launches: the practice screens stop at "allow your microphone" without one.
    launchOptions: { args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] },
    permissions: ["microphone"],
    // Staging may sit behind Vercel's deployment protection.
    extraHTTPHeaders: process.env.VERCEL_AUTOMATION_BYPASS_SECRET
      ? { "x-vercel-protection-bypass": process.env.VERCEL_AUTOMATION_BYPASS_SECRET }
      : undefined,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    actionTimeout: 20_000,
    navigationTimeout: 90_000,
  },
  // CI builds first (E2E_PREBUILT=1) and serves the build; locally the dev server is used.
  webServer: STAGING
    ? undefined
    : {
    command: process.env.E2E_PREBUILT ? "npx next start --port 3101" : "npx next dev --port 3101 --turbopack",
    url: `${WEB}/login`,
    // Only ever reuse a server you started yourself on :3101 with PLATFORM_API_URL pointing at the local api.
    reuseExistingServer: Boolean(process.env.E2E_REUSE_SERVER),
    timeout: 180_000,
    env: { PLATFORM_API_URL: API, NEXT_DIST_DIR: ".next-e2e" },
  },
});
