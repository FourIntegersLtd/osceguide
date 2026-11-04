import assert from "node:assert/strict";
import { test } from "node:test";
import { errorMessage } from "@/foundation/hooks/useAsync";
import { PlatformError } from "@/foundation/platform-client";
import { explainArchiveRefusal } from "@/capabilities/authoring/api/archiveRefusal";

test("an in-use archive refusal names the circuits and sets", () => {
  const cause = new PlatformError(409, {
    code: "not_archivable",
    message: "raw",
    details: { reason: "in_use", circuits: 2, sets: 1 },
  });
  assert.equal(
    errorMessage(explainArchiveRefusal(cause)),
    "This station is on 2 unfinished circuit(s) and 1 practice set(s). Take it off those first, or publish a new version.",
  );
});

test("other failures keep their own message", () => {
  const draft = new PlatformError(409, { code: "not_archivable", message: "raw", details: null });
  assert.equal(explainArchiveRefusal(draft), draft);
  const other = new Error("boom");
  assert.equal(explainArchiveRefusal(other), other);
});
