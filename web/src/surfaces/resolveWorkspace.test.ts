import assert from "node:assert/strict";
import { test } from "node:test";
import type { PlatformUser } from "@/foundation/session";
import { landingWorkspace, resolveWorkspace, workspacesFor } from "./resolveWorkspace";

function userIn(...slugs: string[]): PlatformUser {
  return {
    memberships: slugs.map((slug) => ({
      org_slug: slug,
      org_name: slug,
      org_type: "institution",
      role: "institution_admin",
    })),
  } as unknown as PlatformUser;
}

test("an institution member with nothing remembered lands in the institution", () => {
  assert.equal(landingWorkspace(userIn("kings"), null).slug, "kings");
});

test("a remembered workspace is followed", () => {
  assert.equal(landingWorkspace(userIn("kings", "barts"), "barts").slug, "barts");
});

test("a remembered workspace they have left is ignored", () => {
  assert.equal(landingWorkspace(userIn("kings"), "gone").slug, "kings");
});

test("someone with no membership lands in their own practice", () => {
  assert.equal(landingWorkspace(userIn(), null).slug, "me");
  assert.equal(landingWorkspace(null, null).slug, "me");
});

test("an institution member is offered training beside their institutions", () => {
  assert.deepEqual(workspacesFor(userIn("kings", "barts")).map((w) => w.slug), ["me", "kings", "barts"]);
  assert.equal(landingWorkspace(userIn("kings"), "me").slug, "me");
  assert.equal(landingWorkspace(userIn("kings"), null).slug, "kings");
});

test("someone with no institution is offered their training workspace", () => {
  assert.deepEqual(workspacesFor(userIn()).map((w) => [w.slug, w.name]), [["me", "Training"]]);
});

test("/app/me and the institution both resolve for a member", () => {
  assert.equal(resolveWorkspace("me", userIn("kings"))?.slug, "me");
  assert.equal(resolveWorkspace("me", userIn())?.slug, "me");
  assert.equal(resolveWorkspace("kings", userIn("kings"))?.slug, "kings");
  assert.equal(resolveWorkspace("barts", userIn("kings")), null);
});
