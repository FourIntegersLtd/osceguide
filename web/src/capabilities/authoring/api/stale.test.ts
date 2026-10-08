import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { PlatformError } from "@/foundation/platform-client";
import { staleRefusal } from "@/capabilities/authoring/api/stale";

type Body = ConstructorParameters<typeof PlatformError>[1];
const refusal = (code: string) => new PlatformError(409, { code, message: "server wording" } as Body);

describe("staleRefusal", () => {
  it("turns a stale revision into the sentence the editor shows", () => {
    const error = staleRefusal(refusal("stale_revision"), "marking scheme");
    assert.equal(
      error?.message,
      "Someone else changed this marking scheme just now. We have reloaded it with their changes; make your edit again.",
    );
  });

  it("leaves every other failure alone", () => {
    assert.equal(staleRefusal(refusal("exam_in_use"), "exam"), null);
    assert.equal(staleRefusal(new Error("boom"), "exam"), null);
  });
});
