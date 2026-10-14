import { expect, test } from "@playwright/test";
import { endPeerSession, seedPeerSession } from "../support/db";
import { PHONE, PHONE_SMALL, expectPagesReachable, expectReachableOnPhone } from "../support/phone";
import { dismissOverlays, openPage, signedInAs } from "../support/session";
import { world } from "../support/world";

// On a phone every screen scrolls to its end and nothing scrolls sideways. The live
// rooms (station, peer practice) once filled the screen with a fixed-height flex
// column: the stacked panes were squeezed into it and clipped, and nothing scrolled.
test.use(PHONE);

test("TRAIN-8 the station room scrolls to the end of the doctor information on a phone", async ({ page, context }) => {
  await signedInAs(context, "consumer");
  await openPage(page, "/app/me/mocks");
  await page.getByRole("button", { name: "Create session" }).click();
  await expect(page.getByRole("heading", { level: 1, name: /^Session \d+$/ })).toBeVisible();
  await page.getByRole("link", { name: "Start Session" }).first().click();
  await page.getByRole("button", { name: "Start", exact: true }).click();
  await page.getByRole("button", { name: "Start simulation" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Confirm" }).click();

  const doctorInformation = page.getByRole("heading", { name: "Doctor information" }).locator("xpath=ancestor::section[1]");
  await expect(doctorInformation).toBeVisible();
  await expectReachableOnPhone(page, "station room", doctorInformation.locator("p, li, dd").last());
});

const PEER_HEADING = { preparation: "Preparation Phase", consultation: "Live Consultation" } as const;

test.describe("the peer room on a small phone", () => {
  test.use(PHONE_SMALL);
  for (const [phase, heading] of Object.entries(PEER_HEADING) as [keyof typeof PEER_HEADING, string][]) {
    test(`TRAIN-8 the peer practice room scrolls to its end on a phone (${phase})`, async ({ page, context }) => {
      const w = world();
      // The learner plays the patient: the script beside the call is the whole history.
      const [stationVersionId] = w.stationVersionIds;
      if (!stationVersionId) throw new Error("global setup seeded no station");
      const id = seedPeerSession(w.accounts.newcomer.email, w.accounts.consumer.email, stationVersionId, phase);
      try {
        await signedInAs(context, "consumer");
        await page.goto(`/app/me/marketplace/session/${id}`, { waitUntil: "domcontentloaded" });
        await expect(page.getByRole("heading", { name: heading })).toBeVisible({ timeout: 60_000 });
        await dismissOverlays(page);
        await expectReachableOnPhone(page, `peer ${phase}`);
      } finally {
        endPeerSession(id);
      }
    });
  }
});

const LEARNER_ROUTES = ["dashboard", "mocks", "mocks/list", "library", "stations", "summary", "podcast", "slides", "articles", "achievements", "debriefs", "transcripts", "discussion", "marketplace", "notifications", "settings"].map((route) => `/app/me/${route}`);
const ORG_ROUTES = ["", "/sittings", "/sittings/new", "/trainees", "/team", "/programmes", "/authoring", "/reporting", "/settings", "/stations"];
const STAFF_ROUTES = ["", "/users", "/organizations", "/billing", "/audit", "/ops", "/media", "/moderation", "/announcements", "/growth", "/settings", "/station-flags", "/team", "/messages", "/authoring"].map((route) => `/staff${route}`);

test("TRAIN-8 every learner page scrolls to its end on a phone", async ({ page, context }) => {
  test.setTimeout(480_000); // a route each, compiled on first visit by the dev server
  // The exam-date prompt is a modal (its own journey is exam-date.spec.ts); it would hold the scroll here.
  await context.addInitScript(() => sessionStorage.setItem("exam_date_prompt_skipped", "1"));
  await signedInAs(context, "consumer");
  await expectPagesReachable(page, LEARNER_ROUTES);
});

test("TRAIN-8 every institution and staff page scrolls to its end on a phone", async ({ page, context }) => {
  test.setTimeout(600_000);
  const { slug } = world();
  await signedInAs(context, "admin");
  await expectPagesReachable(page, ORG_ROUTES.map((route) => `/app/${slug}${route}`));
  await signedInAs(context, "platform");
  await expectPagesReachable(page, STAFF_ROUTES);
});
