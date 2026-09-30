import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  PERSONAL_SLUG,
  PERSONAL_WORKSPACE,
  RESERVED_SLUGS,
  isPersonal,
  isWorkspaceSlug,
  workspaceBasePath,
  workspaceKind,
} from "@/foundation/routing/workspace";

describe("workspace", () => {
  it("addresses a personal workspace exactly like an organisation", () => {
    // The whole point of ADR 0002: one grammar, no special case at the root.
    assert.equal(workspaceBasePath(PERSONAL_WORKSPACE), "/app/me");
    assert.equal(workspaceBasePath("kings"), "/app/kings");
  });

  it("reserves the personal slug so no organisation can take it", () => {
    assert.ok(RESERVED_SLUGS.includes(PERSONAL_SLUG));
    assert.ok(RESERVED_SLUGS.includes("staff"));
    assert.ok(RESERVED_SLUGS.includes("app"));
  });

  it("reads an unknown org type as an institution rather than blanking the screen", () => {
    // The backend's own default, and the most restrictive shell.
    assert.equal(workspaceKind("institution"), "institution");
    assert.equal(workspaceKind("partner"), "partner");
    assert.equal(workspaceKind("employer"), "employer");
    assert.equal(workspaceKind("something-new"), "institution");
    assert.equal(workspaceKind(null), "institution");
    assert.equal(workspaceKind(undefined), "institution");
  });

  it("separates personal from organisation workspaces by kind, not by slug", () => {
    assert.ok(isPersonal(PERSONAL_WORKSPACE));
    assert.ok(
      !isPersonal({ kind: "institution", slug: "kings", name: "King's", orgSlug: "kings", role: "owner" }),
    );
  });

  it("rejects slugs that could not address a workspace", () => {
    assert.ok(isWorkspaceSlug("kings"));
    assert.ok(isWorkspaceSlug("st-georges"));
    assert.ok(!isWorkspaceSlug("King's"));
    assert.ok(!isWorkspaceSlug("-leading"));
    assert.ok(!isWorkspaceSlug(""));
  });
});
