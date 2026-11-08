import assert from "node:assert/strict";
import test from "node:test";
import { planCode, retryOnConflict, slugCandidate, slugError } from "@/domains/platform/support";

const PLAN = /^[a-z0-9][a-z0-9_]{1,22}$/;

test("the first slug is the organisation name, as the api's pattern allows", () => {
  assert.equal(slugCandidate("St Mary's Hospital", false), "st-mary-s-hospital");
});

test("a retry slug adds a short suffix and differs per call", () => {
  const a = slugCandidate("Acme", true);
  const b = slugCandidate("Acme", true);
  assert.match(a, /^acme-[a-z0-9]{4}$/);
  assert.notEqual(a, b);
  assert.equal(slugError(a), null);
});

test("a name with no usable letters, or one very long, still gives a valid slug", () => {
  for (const name of ["???", "x", "é".repeat(5), "a".repeat(300)]) {
    for (const suffix of [false, true]) {
      const slug = slugCandidate(name, suffix);
      assert.equal(slugError(slug), null, `${name.slice(0, 8)} ${suffix}`);
      assert.match(slug, /^[a-zA-Z0-9][a-zA-Z0-9-]*$/);
      assert.ok(slug.length >= 2 && slug.length <= 100);
    }
  }
});

test("a plan code matches the api pattern, fits with room for _referral, and differs per call", () => {
  const a = planCode("sca_long_exam_code_here", 30);
  const b = planCode("sca_long_exam_code_here", 30);
  assert.match(a, PLAN);
  assert.ok(a.length <= 23);
  assert.notEqual(a, b);
  assert.match(planCode("SCA", 30), /^sca_1m_[a-z0-9]{4}$/);
  assert.match(planCode("", 5), PLAN);
});

test("retryOnConflict retries a conflict up to three times, then gives up", async () => {
  let calls = 0;
  const conflict = new Error("taken");
  const ok = await retryOnConflict(async (attempt) => {
    calls += 1;
    if (attempt < 2) throw conflict;
    return attempt;
  }, (c) => c === conflict);
  assert.equal(ok, 2);
  assert.equal(calls, 3);

  calls = 0;
  await assert.rejects(
    retryOnConflict(async () => { calls += 1; throw conflict; }, (c) => c === conflict),
    (e) => e === conflict,
  );
  assert.equal(calls, 4);
});

test("retryOnConflict does not retry another error", async () => {
  let calls = 0;
  await assert.rejects(retryOnConflict(async () => { calls += 1; throw new Error("x"); }, () => false));
  assert.equal(calls, 1);
});
