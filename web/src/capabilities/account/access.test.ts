import assert from "node:assert/strict";
import { test } from "node:test";
import { currentPlanView, paidAccess, latestLiveEnd } from "@/capabilities/account/access";
import type { MyEntitlements } from "@/capabilities/account/api";

type Entitlement = MyEntitlements["items"][number];

function grant(over: Partial<Entitlement>): Entitlement {
  return {
    exam_code: "sca",
    live: true,
    source: "purchase",
    ends_at: null,
    ...over,
  } as Entitlement;
}

test("a free account that has chosen an exam holds no paid access", () => {
  // The staging account of 2026-10-03: exam_codes ["sca"], entitlements [].
  assert.equal(holdsPaidAccess([], "sca"), false);
});

test("a live purchase for the current exam is paid access", () => {
  assert.equal(holdsPaidAccess([grant({})], "sca"), true);
});

test("a trial, an expired grant and another exam's grant are not", () => {
  const items = [
    grant({ source: "trial" }),
    grant({ live: false }),
    grant({ exam_code: "plab" }),
  ];
  assert.equal(holdsPaidAccess(items, "sca"), false);
  assert.deepEqual(
    paidAccess(items).map((item) => item.exam_code),
    ["plab"],
  );
});

test("an organisation's grant counts as access", () => {
  assert.equal(holdsPaidAccess([grant({ source: "org_grant" })], "sca"), true);
});

test("with no exam chosen yet, any paid grant counts", () => {
  assert.equal(holdsPaidAccess([grant({ exam_code: "plab" })], null), true);
  assert.equal(holdsPaidAccess([], null), false);
});

test("the end of access is the latest live end, by date, and open-ended wins", () => {
  const ends = (...values: (string | null)[]) => values.map((ends_at) => grant({ ends_at }));
  assert.equal(
    latestLiveEnd(ends("2027-01-05T00:00:00+01:00", "2027-01-04T22:00:00Z")),
    "2027-01-05T00:00:00+01:00",
  );
  assert.equal(latestLiveEnd(ends("2027-01-05T00:00:00Z", null)), null);
  assert.equal(latestLiveEnd([grant({ live: false, ends_at: "2030-01-01T00:00:00Z" })]), null);
});

const TRIAL_LIMITS = { stations: 3, days: 7, attempts_per_station: 2 };
const NOW = new Date("2026-10-11T12:00:00Z");
const mine = (items: Entitlement[]): MyEntitlements => ({
  items,
  trial: TRIAL_LIMITS,
  next_cursor: null,
  can_upgrade: true,
});
test("current plan: no access reads Free with the trial's station allowance", () => {
  assert.deepEqual(currentPlanView(mine([]), NOW), {
    kind: "free",
    title: "Free",
    meta: "You can try 3 stations",
    active: false,
    upgrade: true,
  });
});

test("current plan: a running trial counts its days left and its end", () => {
  const trial = grant({ source: "trial", ends_at: "2026-10-14T12:00:00Z" });
  assert.deepEqual(currentPlanView(mine([trial]), NOW), {
    kind: "trial",
    title: "Free trial, 3 days left",
    meta: "Ends 14 October 2026",
    active: true,
    upgrade: true,
  });
  const lastDay = grant({ source: "trial", ends_at: "2026-10-11T18:00:00Z" });
  assert.equal(currentPlanView(mine([lastDay]), NOW).title, "Free trial, 1 day left");
});

test("current plan: a purchase reads from its grant's own dates, and beats a trial", () => {
  const items = [
    grant({ source: "trial", ends_at: "2026-10-14T12:00:00Z" }),
    grant({ starts_at: "2026-10-01T12:00:00Z", ends_at: "2027-01-01T12:00:00Z" }),
  ];
  assert.deepEqual(currentPlanView(mine(items), NOW), {
    kind: "paid",
    title: "Full access",
    meta: "Started 1 October 2026, ends 1 January 2027",
    active: true,
    upgrade: true,
  });
});

test("current plan: a second plan queued after the running one extends the end, not the start", () => {
  const items = [
    grant({ starts_at: "2027-01-01T12:00:00Z", ends_at: "2027-07-01T12:00:00Z" }),
    grant({ starts_at: "2026-10-01T12:00:00Z", ends_at: "2027-01-01T12:00:00Z" }),
  ];
  assert.equal(currentPlanView(mine(items), NOW).meta, "Started 1 October 2026, ends 1 July 2027");
});

test("current plan: a refunded newer purchase does not speak for the older one still running", () => {
  const items = [
    grant({ live: false, revoked_at: "2026-10-10T12:00:00Z", starts_at: "2026-10-09T12:00:00Z", ends_at: "2027-04-09T12:00:00Z" }),
    grant({ starts_at: "2026-10-01T12:00:00Z", ends_at: "2026-11-01T12:00:00Z" }),
  ];
  assert.equal(currentPlanView(mine(items), NOW).meta, "Started 1 October 2026, ends 1 November 2026");
});

test("current plan: access that has run out says so instead of offering the trial again", () => {
  const ended = currentPlanView(mine([grant({ live: false, ends_at: "2026-10-01T12:00:00Z" })]), NOW);
  assert.deepEqual([ended.kind, ended.meta, ended.active], ["free", "Your access has ended", false]);
  const trialOver = currentPlanView(mine([grant({ source: "trial", live: false, ends_at: "2026-10-05T12:00:00Z" })]), NOW);
  assert.equal(trialOver.meta, "Your free trial has ended");
});

test("current plan: an organisation's grant is not offered a checkout", () => {
  assert.deepEqual(
    currentPlanView(mine([grant({ source: "org_grant", ends_at: "2027-06-30T12:00:00Z" })]), NOW),
    { kind: "organisation", title: "Organisation access", meta: "Ends 30 June 2027", active: true, upgrade: false },
  );
  assert.equal(currentPlanView(mine([grant({ source: "sso_tenant" })]), NOW).meta, "No end date");
});
