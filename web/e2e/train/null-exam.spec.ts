import { expect, test, type Page } from "@playwright/test";
import { dismissOverlays, openPage, signedInAs } from "../support/session";

// TRAIN-13: when the app does not know the person's exam (the dashboard read failed, or the api
// named none) a screen that asks the api about an exam says so, offers "Try again" and asks
// nothing: no form, no actions, and above all no paywall. `currentExam ?? ""` once reached
// `accessState(workspace, "")`, a genuine `hasPaid: false`, and a subscriber saw "0 of 3 free
// stations". The wiring lives in `.tsx` (RequireExam, PeerPractice) which a node test cannot
// import, so this is its only guard.
const DASHBOARD = "**/api/v1/me/dashboard*";

/** The two ways the app ends up with no exam: the read fails, or it answers with none. */
const BREAKS = {
  "the dashboard read fails (502)": async (page: Page) => {
    await page.route(DASHBOARD, (route) => route.fulfill({ status: 502, contentType: "application/json", body: "{}" }));
  },
  "the api names no exam": async (page: Page) => {
    await page.route(DASHBOARD, async (route) => {
      const real = await route.fetch();
      const dashboard = (await real.json()) as Record<string, unknown>;
      await route.fulfill({
        response: real,
        json: { ...dashboard, current_exam_code: null, current_exam: null, exam_codes: [] },
      });
    });
  },
};

const SCREENS = [
  {
    name: "mocks, Setup tab",
    path: "/app/me/mocks",
    explained: (page: Page) => page.getByText("We don't know your exam yet"),
    back: (page: Page) => page.getByText("Session setup"),
    paywall: true,
  },
  {
    name: "mocks, Combine tab",
    path: "/app/me/mocks?tab=combine",
    explained: (page: Page) => page.getByText("We don't know your exam yet"),
    back: (page: Page) => page.getByRole("heading", { name: "Build a focused session" }),
    paywall: false,
  },
  {
    name: "marketplace",
    path: "/app/me/marketplace",
    explained: (page: Page) => page.getByText(/so the marketplace is unavailable/),
    back: (page: Page) => page.getByRole("button", { name: "Post availability" }),
    paywall: false,
  },
];

for (const screen of SCREENS) {
  for (const [breakage, apply] of Object.entries(BREAKS)) {
    test(`TRAIN-13 ${screen.name}: when ${breakage} it explains, offers a retry and shows no paywall`, async ({ page, context }) => {
      await signedInAs(context, "consumer");
      await apply(page);
      await openPage(page, screen.path);
      await dismissOverlays(page);

      const main = page.getByRole("main");
      await expect(screen.explained(page)).toBeVisible();
      await expect(main.getByRole("button", { name: "Try again" })).toBeVisible();
      // The shipped bug: no exam was read as "". The paywall and the progress bar must not exist.
      await expect(page.getByRole("progressbar")).toHaveCount(0);
      await expect(page.getByText(/free stations/i)).toHaveCount(0);
      await expect(page.getByText(/Create session|Post availability/)).toHaveCount(0);
      await expect(screen.back(page)).toHaveCount(0);

      // The retry is the only recovery: once the api answers, the screen is back with the real exam.
      await page.unroute(DASHBOARD);
      await main.getByRole("button", { name: "Try again" }).click();
      await expect(screen.back(page)).toBeVisible();
      if (screen.paywall) await expect(page.getByRole("progressbar")).toBeVisible();
    });
  }
}
