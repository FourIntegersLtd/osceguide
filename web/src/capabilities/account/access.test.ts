import assert from "node:assert/strict";
import { test } from "node:test";
import { holdsPaidAccess, paidAccess } from "@/capabilities/account/access";
import type { Entitlement } from "@/capabilities/account/api";

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
