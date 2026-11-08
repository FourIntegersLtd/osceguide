import assert from "node:assert/strict";
import { test } from "node:test";
import { workspaceKind, type Workspace } from "@/foundation/routing";
import { CONSOLE_TARGET, currentTargetKey, workspaceTarget } from "./switcherTargets";

const staffOrg: Workspace = {
  kind: workspaceKind("institution"),
  slug: "staff",
  name: "Staff Ltd",
  orgSlug: "staff",
  role: "institution_admin",
} as Workspace;

test("an organisation slugged staff is not the console", () => {
  assert.notEqual(workspaceTarget(staffOrg).key, CONSOLE_TARGET.key);
  assert.equal(currentTargetKey(null), CONSOLE_TARGET.key);
  assert.notEqual(currentTargetKey(staffOrg), CONSOLE_TARGET.key);
  assert.equal(currentTargetKey(staffOrg), workspaceTarget(staffOrg).key);
});

test("the console re-mints for the own practice and opens /staff", () => {
  assert.equal(CONSOLE_TARGET.orgSlug, null);
  assert.equal(CONSOLE_TARGET.href, "/staff");
});
