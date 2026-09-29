import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { AuditPage } from "@/domains/assess/team/api";
import { auditMatches } from "@/domains/assess/team/support";

const entry = (over: Partial<AuditPage["items"][number]> = {}): AuditPage["items"][number] =>
  ({
    id: "a1",
    action: "membership.invited",
    actor_email: "Lead@Kings.ac.uk",
    at: "2026-09-29T09:00:00Z",
    summary: null,
    target_id: null,
    target_type: null,
    ...over,
  }) as AuditPage["items"][number];

describe("audit filters, as the platform audit decides them", () => {
  it("matches the actor's address exactly, in any case", () => {
    assert.equal(auditMatches(entry(), { actorEmail: "lead@kings.ac.uk" }), true);
    assert.equal(auditMatches(entry(), { actorEmail: "lead@kings" }), false);
    assert.equal(auditMatches(entry({ actor_email: null }), { actorEmail: "lead@kings.ac.uk" }), false);
  });

  it("matches the action by prefix", () => {
    assert.equal(auditMatches(entry(), { action: "membership." }), true);
    assert.equal(auditMatches(entry(), { action: "roster." }), false);
  });

  it("matches everything with no filters", () => {
    assert.equal(auditMatches(entry(), {}), true);
  });
});
