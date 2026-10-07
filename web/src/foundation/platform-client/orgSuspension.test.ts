import assert from "node:assert/strict";
import { afterEach, test } from "node:test";
import { platformRequest } from "@/foundation/platform-client/client";
import { switchWorkspace } from "@/foundation/platform-client/auth";
import {
  isOrgSuspended,
  resetOrgSuspensionForTests,
  subscribeOrgSuspension,
} from "@/foundation/platform-client/orgSuspension";

const realFetch = globalThis.fetch;

afterEach(() => {
  globalThis.fetch = realFetch;
  resetOrgSuspensionForTests();
});

function refuse(code: string): void {
  globalThis.fetch = (async () =>
    Response.json({ code, message: "refused" }, { status: 403 })) as typeof fetch;
}

test("one suspended refusal marks that organisation, and only it, for the workspace frame", async () => {
  let told = 0;
  const stop = subscribeOrgSuspension(() => (told += 1));
  refuse("organization_suspended");
  await platformRequest("/api/v1/orgs/riverside/sittings").catch(() => undefined);
  await platformRequest("/api/v1/orgs/riverside/trainees").catch(() => undefined);
  stop();

  assert.equal(isOrgSuspended("riverside"), true);
  assert.equal(isOrgSuspended("kings"), false);
  assert.equal(told, 1, "the frame re-renders once, not once per panel");
});

test("an ordinary 403 is not a suspension", async () => {
  refuse("forbidden");
  await platformRequest("/api/v1/orgs/elsewhere/sittings").catch(() => undefined);
  assert.equal(isOrgSuspended("elsewhere"), false);
});

test("switching into a suspended organisation marks it by name", async () => {
  refuse("organization_suspended");
  await switchWorkspace("kings").catch(() => undefined);
  assert.equal(isOrgSuspended("kings"), true);
});
