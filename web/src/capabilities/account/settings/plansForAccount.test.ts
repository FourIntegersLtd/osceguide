import assert from "node:assert/strict";
import { test } from "node:test";
import type { Plan } from "@/capabilities/account/api";
import { plansForAccount } from "@/capabilities/account/settings/plansForAccount";

const plan = (code: string, exam: string) => ({ code, exam_code: exam }) as Plan;
const plans = [plan("sca_1m", "sca"), plan("plab_1m", "plab")];

test("a signed-in account is offered its server-held exam's plans only", () => {
  assert.deepEqual(plansForAccount(plans, "sca").map((p) => p.code), ["sca_1m"]);
});

test("the exam is the server's, however it is spelt, never a browser setting", () => {
  assert.deepEqual(plansForAccount(plans, "SCA").map((p) => p.code), ["sca_1m"]);
});

test("an account with no exam yet is offered every plan", () => {
  assert.equal(plansForAccount(plans, null).length, 2);
});
