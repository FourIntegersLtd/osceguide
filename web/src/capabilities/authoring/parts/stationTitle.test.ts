import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { renamedTitle } from "@/capabilities/authoring/parts/stationTitle";

describe("renamedTitle", () => {
  it("is not a rename when only whitespace differs", () => {
    assert.equal(renamedTitle("Chest pain ", "Chest pain"), undefined);
    assert.equal(renamedTitle("Chest pain ", "Chest pain "), undefined);
    assert.equal(renamedTitle("Chest pain", " Chest pain  "), undefined);
  });

  it("returns the trimmed new title otherwise", () => {
    assert.equal(renamedTitle(" Chest pain 2 ", "Chest pain"), "Chest pain 2");
  });
});
