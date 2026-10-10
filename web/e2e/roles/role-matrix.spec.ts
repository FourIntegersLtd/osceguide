import { expect, test, type Page } from "@playwright/test";
import { sidebar } from "../support/menu";
import { openPage, signedInAs } from "../support/session";
import { needRole, world, type Role } from "../support/world";

/**
 * ROLES-1: open every page the menu offers each seeded role, in its own
 * workspace, and fail on any refused call or "Page not found". A menu item
 * that leads to a 403 is the bug this catches (the Hire candidate once saw
 * "Sittings", a staff read, and got a permission error).
 *
 * The pages are discovered from the sidebar the role is actually shown, so a
 * new nav item is covered the day it is added.
 */
const MATRIX: { role: Role; home: (w: ReturnType<typeof world>) => string; label: string }[] = [
  { role: "admin", home: (w) => `/app/${w.slug}/dashboard`, label: "institution admin" },
  { role: "supervisor", home: (w) => `/app/${w.slug}/dashboard`, label: "supervisor" },
  { role: "trainee", home: (w) => `/app/${w.slug}/trainee`, label: "trainee" },
  { role: "consumer", home: () => "/app/me/dashboard", label: "consumer" },
  { role: "hireAdmin", home: (w) => `/app/${w.hireSlug}/dashboard`, label: "employer admin" },
  { role: "hireCandidate", home: (w) => `/app/${w.hireSlug}/trainee`, label: "employer candidate" },
  { role: "partnerAdmin", home: (w) => `/app/${w.partnerSlug}/dashboard`, label: "partner admin" },
  { role: "platform", home: () => "/staff", label: "platform admin" },
];

/** Refused or missing api answers seen while a page loads. */
function watchRefusals(page: Page): string[] {
  const seen: string[] = [];
  page.on("response", (response) => {
    const url = response.url();
    if (url.includes("/api/v1/") && [401, 403, 404].includes(response.status())) seen.push(`${response.status()} ${response.request().method()} ${new URL(url).pathname}`);
  });
  return seen;
}

for (const { role, home, label } of MATRIX) {
  test(`ROLES-1 ${label}: every page in the menu opens @staging`, async ({ page, context }) => {
    needRole(role);
    const w = world();
    await signedInAs(context, role);
    const refusals = watchRefusals(page);

    await openPage(page, home(w));
    const prefix = home(w).startsWith("/staff") ? "/staff" : `/app/${home(w).split("/")[2]}`;
    await sidebar(page).waitFor();
    const hrefs = await sidebar(page)
      .locator("a[href]")
      .evaluateAll((links) => links.map((link) => link.getAttribute("href") ?? ""));
    const pages = [...new Set([home(w), ...hrefs.filter((href) => href.startsWith(prefix))])];
    expect(pages.length, `${label} should be shown a menu`).toBeGreaterThan(1);
    // Each page can take up to openPage's 60s on a slow staging: budget for the whole menu.
    test.setTimeout(60_000 + 30_000 * pages.length);

    for (const path of pages) {
      refusals.length = 0;
      await openPage(page, path);
      await expect(page.getByRole("heading", { name: "Page not found" }), `${label} on ${path}`).toHaveCount(0);
      // Settled: the page's own data calls have answered (the loading placeholder is gone).
      await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 45_000 });
      expect(refusals, `${label} on ${path}: the page's own calls were refused`).toEqual([]);
    }
  });
}
