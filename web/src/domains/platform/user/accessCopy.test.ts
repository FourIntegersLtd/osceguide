import assert from "node:assert/strict";
import test from "node:test";
import { formatDay } from "@/domains/platform/support/vocabulary";
import type { PlatformAccessGrant, PlatformExamAccess } from "@/domains/platform/support/api";
import {
  GRANT_STATE_LABEL,
  accessLine,
  giveAccessLabel,
  grantPaymentLine,
  grantState,
  hasPlanToQueueBehind,
  planDurationLabel,
  planName,
} from "@/domains/platform/user/accessCopy";

const plans = new Map([["sca_6m", 180]]);
const row = (overrides: Partial<PlatformExamAccess>): PlatformExamAccess => ({
  exam_code: "sca",
  grants: [],
  limit_reason: "plan:sca_6m",
  station_limit: 103,
  stations_sat: 42,
  ...overrides,
});
const grant = (overrides: Partial<PlatformAccessGrant>): PlatformAccessGrant => ({
  amount_total_pence: null,
  currency: null,
  entitlement_id: "g1",
  ends_at: null,
  live: false,
  paid_at: null,
  payment_id: null,
  payment_reference: null,
  plan_code: null,
  receipt_id: null,
  revoked_at: null,
  source: "purchase",
  starts_at: "2026-01-01T00:00:00Z",
  ...overrides,
});

test("a plan line says how many stations are used and left", () => {
  assert.equal(accessLine(row({}), plans), "SCA: 6-month plan. 42 of 103 stations used, 61 left.");
});

test("organisation grants and no access read plainly", () => {
  assert.equal(
    accessLine(row({ limit_reason: "unlimited:org_grant", station_limit: null }), plans),
    "SCA: Unlimited because of an organisation grant",
  );
  assert.equal(accessLine(row({ limit_reason: "no_access", station_limit: 0 }), plans), "SCA: No access");
});

test("a grant is live, starts later or ended", () => {
  const now = new Date("2026-06-01T00:00:00Z");
  assert.equal(grantState(grant({ live: true }), now), "live");
  assert.equal(grantState(grant({ starts_at: "2026-09-01T00:00:00Z" }), now), "starts_later");
  assert.equal(grantState(grant({ ends_at: "2026-02-01T00:00:00Z" }), now), "ended");
});

test("a revoked grant reads Revoked, even one that had not started yet", () => {
  const now = new Date("2026-06-01T00:00:00Z");
  const revoked = grant({ revoked_at: "2026-03-01T00:00:00Z", starts_at: "2026-09-01T00:00:00Z" });
  assert.equal(grantState(revoked, now), "revoked");
  assert.equal(GRANT_STATE_LABEL[grantState(revoked, now)], "Revoked");
  assert.equal(grantState(grant({ revoked_at: "2026-03-01T00:00:00Z", live: false }), now), "revoked");
});

test("plan lengths and start choices are in lay words", () => {
  assert.equal(planDurationLabel(30), "1-month plan");
  assert.equal(planDurationLabel(45), "45-day plan");
});

test("a plan is named by its exam and length, not its code", () => {
  assert.equal(planName({ exam_code: "sca", duration_days: 180 }), "SCA 6-month plan");
});

test("a bought grant says what it cost and its receipt, a free place says so, an unbought one says nothing", () => {
  const paid = grant({
    amount_total_pence: 2499,
    currency: "gbp",
    paid_at: "2026-11-03T07:23:00Z",
    receipt_id: "RCP-sca-e018fedb",
  });
  assert.equal(grantPaymentLine(paid), `£24.99 paid ${formatDay(paid.paid_at)} · receipt RCP-sca-e018fedb`);
  const free = grant({ amount_total_pence: 0, currency: "gbp", paid_at: "2026-11-03T07:23:00Z" });
  assert.equal(grantPaymentLine(free), `Free place given ${formatDay(free.paid_at)} · no receipt`);
  assert.equal(grantPaymentLine(grant({ source: "trial" })), null);
});

test("when it starts is only asked when a bought plan is running or queued", () => {
  const now = new Date("2026-06-01T00:00:00Z");
  assert.equal(hasPlanToQueueBehind(undefined, now), false);
  assert.equal(hasPlanToQueueBehind(row({ grants: [grant({ live: true })] }), now), true);
  assert.equal(hasPlanToQueueBehind(row({ grants: [grant({ starts_at: "2026-09-01T00:00:00Z" })] }), now), true);
  assert.equal(hasPlanToQueueBehind(row({ grants: [grant({ live: true, source: "trial" })] }), now), false);
  assert.equal(hasPlanToQueueBehind(row({ grants: [grant({ revoked_at: "2026-03-01T00:00:00Z" })] }), now), false);
});

test("the give-access button names the plan and the price", () => {
  const plan = { exam_code: "sca", duration_days: 30 };
  assert.equal(giveAccessLabel(plan, 2499), "Give SCA 1-month plan for £24.99");
  assert.equal(giveAccessLabel(plan, null), "Give SCA 1-month plan for free");
  assert.equal(giveAccessLabel(plan, 0), "Give SCA 1-month plan for free");
});
