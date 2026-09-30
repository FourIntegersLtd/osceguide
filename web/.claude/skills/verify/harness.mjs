/**
 * The browser half of the verify skill: sign in the way a person does, open a
 * page, and write proof. Import it from a throwaway script run inside
 * platform-web/ (playwright-core only resolves from there):
 *
 *   import { start, signIn, open, proof, finish } from "./.claude/skills/verify/harness.mjs";
 *   const run = await start("my-check");
 *   await signIn(run);
 *   await open(run, "/app/kings/dashboard");
 *   await proof(run, "dashboard");
 *   await finish(run);
 *
 * Every artifact lands in .verify/<run-id>/ (gitignored) and survives cleanup.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { chromium } from "playwright-core";
import { signInWithPassword } from "../../../scripts/admin-totp.mjs";

export const WEB = process.env.VERIFY_WEB_URL ?? "http://localhost:3100";
export const API = process.env.VERIFY_API_URL ?? "http://127.0.0.1:8002";
const CHROME = process.env.VERIFY_CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";

// A seeded test account: platform admin, owner of `kings`, partner admin of
// `bmj`, institution admin of `st-marys`. Never drive a real person's account;
// the local database holds imported production users.
export const ACCOUNT = {
  email: process.env.VERIFY_EMAIL ?? "walkthrough@example.com",
  password: process.env.VERIFY_PASSWORD ?? "correct horse battery",
};

export async function start(label) {
  const id = `${new Date().toISOString().replace(/[:.]/g, "-")}-${label}`;
  const dir = join(".verify", id);
  mkdirSync(dir, { recursive: true });
  // A fake microphone, so the voice screens (station practice, Athena) can
  // connect instead of stopping at "your browser is blocking the microphone".
  const browser = await chromium.launch({
    executablePath: CHROME,
    args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"],
  });
  const context = await browser.newContext({
    viewport: { width: 1366, height: 900 },
    permissions: ["microphone"],
  });
  const page = await context.newPage();
  const problems = [];
  page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
  page.on("console", (m) => {
    if (m.type() === "error") problems.push(`console: ${m.text().slice(0, 200)}`);
  });
  page.on("response", (r) => {
    // 404s too, so a bare "Failed to load resource" console line has a URL.
    if (r.status() >= 500 || r.status() === 404) problems.push(`${r.status()} ${r.request().method()} ${r.url()}`);
  });
  return { id, dir, browser, context, page, problems, steps: [] };
}

function note(run, line) {
  run.steps.push(line);
  console.log(line);
}

/**
 * Sign in through the real form. `/login` must be fully hydrated first: a
 * submit on the server-rendered HTML posts the form as a GET, and every later
 * page then bounces to /login?next= — which looks exactly like a session bug.
 */
export async function signIn(run, account = ACCOUNT) {
  const { page } = run;
  const probe = await fetch(`${API}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(account),
  });
  const body = await probe.json().catch(() => null);
  // The login form does not collect a second factor yet. A platform admin
  // (and anyone else already enrolled) finishes here, then the same cookie
  // the form would have set is stored on the browser.
  if (body?.status === "mfa_required" || body?.status === "mfa_enrolment_required") {
    const session = await signInWithPassword(API, account.email, account.password);
    const stored = await page.request.post(`${WEB}/api/session`, {
      data: {
        access_token: session.access_token,
        refresh_token: session.refresh_token,
        expires_in: session.expires_in,
      },
    });
    if (!stored.ok()) throw new Error(`session cookie ${stored.status()}`);
    await page.goto(WEB, { waitUntil: "domcontentloaded", timeout: 90_000 });
    await page.waitForURL(/\/(app|staff)(\/|$)/, { timeout: 30_000 }).catch(async (cause) => {
      await proof(run, "sign-in-failed");
      throw cause;
    });
    note(run, `signed in as ${account.email} -> ${page.url().replace(WEB, "")}`);
    return;
  }
  await page.goto(`${WEB}/login`, { waitUntil: "networkidle", timeout: 90_000 });
  await page.waitForTimeout(1500);
  // A fresh browser gets the cookie dialog, and its scrim swallows every click.
  const decline = page.getByRole("button", { name: "Continue without analytics" });
  if (await decline.isVisible()) await decline.click();
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Password", { exact: true }).fill(account.password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  // A platform admin lands on /staff, everyone else on /app/<workspace>.
  await page.waitForURL(/\/(app|staff)(\/|$)/, { timeout: 30_000 }).catch(async (cause) => {
    await proof(run, "sign-in-failed");
    throw cause;
  });
  note(run, `signed in as ${account.email} -> ${page.url().replace(WEB, "")}`);
}

/**
 * Open a path and wait until the screen has actually rendered. `networkidle`
 * never settles on a dev server's first compile, and a "Loading" status can
 * clear before the real content arrives, so this waits for `ready` — a
 * locator, or by default the page's first <h1>. A first compile can take 30s.
 */
export async function open(run, path, { ready, settle = 500 } = {}) {
  const res = await run.page.goto(`${WEB}${path}`, { waitUntil: "domcontentloaded", timeout: 90_000 });
  const target = ready ? ready(run.page) : run.page.locator("h1").first();
  await target
    .waitFor({ state: "visible", timeout: 60_000 })
    .catch(() => note(run, `  not ready after 60s: ${path}`));
  await run.page.waitForTimeout(settle);
  note(run, `open ${path} [${res?.status()}] -> ${run.page.url().replace(WEB, "")}`);
  return res?.status();
}

/** A screenshot plus the ARIA tree of <main> (or <body>), both named `name`. */
export async function proof(run, name) {
  const { page, dir } = run;
  await page.screenshot({ path: join(dir, `${name}.png`), fullPage: true });
  const root = (await page.locator("main").count()) ? page.locator("main").first() : page.locator("body");
  writeFileSync(join(dir, `${name}.aria.txt`), await root.ariaSnapshot());
  note(run, `proof ${name} -> ${join(dir, name)}.{png,aria.txt}`);
}

/** Close the browser and write the step log and any problems. Returns problem count. */
export async function finish(run) {
  const problems = [...new Set(run.problems)];
  writeFileSync(join(run.dir, "run.log"), [...run.steps, "", "problems:", ...problems].join("\n") + "\n");
  await run.browser.close();
  console.log(`\nproblems: ${problems.length ? "\n" + problems.slice(0, 15).join("\n") : "none"}`);
  console.log(`evidence: ${run.dir}`);
  return problems.length;
}
