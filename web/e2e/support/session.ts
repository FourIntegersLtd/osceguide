import type { BrowserContext, Page } from "@playwright/test";
import { loginPatiently, WEB, type Session } from "./api";
import { world, type Role } from "./world";

const cache = new Map<Role, Session>();

/** Token pair for a world account, signed in once per worker (sign-ins are rate limited). */
export async function sessionFor(role: Role): Promise<Session> {
  const known = cache.get(role);
  if (known) return known;
  const account = world().accounts[role];
  const session = await loginPatiently(account.email, account.password);
  cache.set(role, session);
  return session;
}

/**
 * Give a browser context the cookie the login form would have set, so the
 * journey starts from the screen it is about. The form itself is exercised by
 * train/sign-in.spec.ts through the verify harness.
 */
export async function signedInAs(context: BrowserContext, role: Role): Promise<void> {
  const session = await sessionFor(role);
  const stored = await context.request.post(`${WEB}/api/session`, {
    data: { access_token: session.access_token, refresh_token: session.refresh_token, expires_in: session.expires_in },
  });
  if (!stored.ok()) throw new Error(`session cookie ${stored.status()}`);
}

/**
 * A fresh browser gets the cookie dialog, and a learner's first visit gets
 * Athena's walkthrough (a voice feature, so the journeys close it). Both put a
 * scrim over the page that swallows every click.
 */
export async function dismissOverlays(page: Page): Promise<void> {
  // The walkthrough sits above the cookie dialog: close the top one, then look again.
  const close = page.getByRole("button", { name: "Close dialog" });
  const decline = page.getByRole("button", { name: "Continue without analytics" });
  for (let round = 0; round < 6; round += 1) {
    // The dialogs mount after hydration, which is slow on a cold dev server: give them time.
    const wait = round === 0 ? 4_000 : 2_000;
    // A short click: the walkthrough can mount over the cookie dialog after the check above,
    // and a blocked click then waits the full action timeout. Fail fast and look again.
    if (await close.isVisible({ timeout: wait }).catch(() => false)) await close.click({ timeout: 2_000 }).catch(() => undefined);
    else if (await decline.isVisible({ timeout: wait }).catch(() => false)) await decline.click({ timeout: 2_000 }).catch(() => undefined);
    else return;
  }
}

/**
 * Open a page and wait until it has rendered its heading, then clear any overlay.
 * Screens that fetch before they draw show no heading when the call fails, only
 * an alert, so an alert is reported with the path instead of a bare timeout.
 */
export async function openPage(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "domcontentloaded" });
  try {
    await page
      .getByRole("heading", { level: 1 })
      .first()
      .waitFor({ state: "visible", timeout: 60_000 });
  } catch (cause) {
    throw new Error(`${path}: no h1 within 60s (at ${page.url()})`, { cause });
  }
  await dismissOverlays(page);
}
