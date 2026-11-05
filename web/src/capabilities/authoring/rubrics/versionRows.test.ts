import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { versionRows } from "@/capabilities/authoring/rubrics/versionRows";
import type { RubricVersion } from "@/capabilities/authoring/api/scope";

const v = (version: number, status: string, published_at?: string) => ({ id: `id${version}`, version, status, published_at }) as RubricVersion;

describe("versionRows", () => {
  it("marks the draft, the newest published as Live and older ones as Old", () => {
    const rows = versionRows([v(2, "published", "2026-09-04T10:00:00Z"), v(4, "draft"), v(3, "published", "2026-10-02T10:00:00Z"), v(1, "archived")], "id3");
    assert.deepEqual(rows.map((r) => [r.version, r.chip.label, r.detail]),[
      [4, "Draft", "Draft"],
      [3, "Live", "Published 2 Oct 2026"],
      [2, "Old", "Published 4 Sept 2026"],
      [1, "Archived", "Archived"],
    ]);
  });
});
