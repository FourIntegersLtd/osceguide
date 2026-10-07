import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { practisableStation } from "@/domains/assess/trainee/practisableStation";
import type { OrgStation } from "@/domains/assess/trainee/api";

const row = (id: string, status: string, versionId: string | null): OrgStation =>
  ({ id, status, current_version_id: versionId }) as OrgStation;

describe("practisableStation", () => {
  const stations = [row("pub", "published", "v1"), row("draft", "draft", null), row("old", "archived", "v0")];

  it("finds a published station", () => {
    assert.equal(practisableStation(stations, "pub")?.id, "pub");
  });

  it("is null for a missing, draft or archived station, so the page can say so", () => {
    assert.equal(practisableStation(stations, "nope"), null);
    assert.equal(practisableStation(stations, "draft"), null);
    assert.equal(practisableStation(stations, "old"), null);
  });
});
