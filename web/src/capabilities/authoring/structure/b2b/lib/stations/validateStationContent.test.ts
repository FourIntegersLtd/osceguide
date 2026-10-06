import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  inSentence,
  validateStationContent,
} from "@/capabilities/authoring/structure/b2b/lib/stations/validateStationContent";
import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";

describe("a missing required field", () => {
  it("reads as a sentence, not a quoted label", () => {
    const structure = {
      sections: [
        { id: "s", title: "S", blocks: [{ id: "bio", type: "shortText", label: "Patient Biodata", required: true }] },
      ],
    } as unknown as StationStructure;
    const result = validateStationContent(structure, {});
    assert.deepEqual(result, { ok: false, errors: ["Patient biodata is required"] });
  });

  it("keeps an acronym", () => {
    assert.equal(inSentence("SCA Task Brief"), "SCA task brief");
  });
});
