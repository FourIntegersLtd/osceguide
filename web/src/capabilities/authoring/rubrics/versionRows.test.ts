import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { versionRows } from "@/capabilities/authoring/rubrics/versionRows";
import type { RubricVersion } from "@/capabilities/authoring/api/scope";

const v = (version: number, status: string, extra: Partial<RubricVersion> = {}) =>
  ({ id: `id${version}`, version, status, ...extra }) as RubricVersion;
const NOW = new Date(2026, 9, 20, 15, 0);

describe("versionRows", () => {
  it("marks the draft, the newest published as Live and older ones as Old", () => {
    const rows = versionRows([v(2, "published", { published_at: "2026-09-04T10:00:00Z" }), v(4, "draft", { updated_at: new Date(2026, 9, 20, 9, 0).toISOString() }), v(3, "published", { published_at: "2026-10-02T10:00:00Z", used_by_exams: ["PLAB 2", "SCA"] }), v(1, "archived", { archived_at: "2026-09-30T10:00:00Z" })], "id3", NOW);
    assert.deepEqual(rows.map((r) => [r.version, r.chip.label, r.detail]),[
      [4, "Draft", "Draft, edited today"],
      [3, "Live", "Published 2 Oct 2026 · used by PLAB 2, SCA"],
      [2, "Old", "Published 4 Sept 2026"],
      [1, "Archived", "Archived 30 Sept 2026"],
    ]);
  });

  it("dates a draft edited on an earlier day", () => {
    const rows = versionRows([v(2, "draft", { updated_at: "2026-10-02T10:00:00Z" })], null, NOW);
    assert.equal(rows[0]?.detail, "Draft, edited 2 Oct 2026");
  });
});
