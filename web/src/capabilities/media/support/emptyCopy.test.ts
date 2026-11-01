import assert from "node:assert/strict";
import { test } from "node:test";
import { emptyLibraryDescription } from "@/capabilities/media/support/emptyCopy";

test("with an exam picked, the empty library names it in capitals and points to an upgrade", () => {
  assert.equal(
    emptyLibraryDescription("plab2", "Check back later for new content."),
    "Nothing published for PLAB2 yet. Upgrade for full access.",
  );
});

test("with no exam, the caller's own line is returned untouched", () => {
  assert.equal(emptyLibraryDescription(null, "Check back later for new content."), "Check back later for new content.");
  assert.equal(emptyLibraryDescription(undefined, "Episodes appear here as they are published."), "Episodes appear here as they are published.");
  assert.equal(emptyLibraryDescription("", "x"), "x");
});
