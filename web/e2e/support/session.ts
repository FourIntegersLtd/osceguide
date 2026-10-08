import type { BrowserContext, Page } from "@playwright/test";
import { loginPatiently, PASSWORD, WEB, type Session } from "./api";
import { world, type Role } from "./world";

const cache = new Map<Role, Session>();

/** Token pair for a world account, signed in once per worker (sign-ins are rate limited). */
export async function sessionFor(role: Role): Promise<Session> {
  const known = cache.get(role);
  if (known) return known;
  const session = await loginPatiently(world().accounts[role].email, PASSWORD);
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
  for (let round = 0; round < 4; round += 1) {
    // The dialogs mount after hydration, which is slow on a cold dev server: give them time.
    const wait = round === 0 ? 4_000 : 2_000;
    if (await close.isVisible({ timeout: wait }).catch(() => false)) await close.click();
    else if (await decline.isVisible({ timeout: wait }).catch(() => false)) await decline.click();
    else return;
  }
}

/** Open a page and wait until it has rendered its heading, then clear any overlay. */
export async function openPage(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: "domcontentloaded" });
  await page.getByRole("heading", { level: 1 }).first().waitFor({ state: "visible", timeout: 60_000 });
  await dismissOverlays(page);
}
