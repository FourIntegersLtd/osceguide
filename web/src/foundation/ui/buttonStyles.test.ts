import assert from "node:assert/strict";
import { test } from "node:test";
import { getButtonClassName } from "./buttonStyles";

test("commit button is the one filled action, on the commit token", () => {
  for (const themeType of ["b2c", "b2b"] as const) {
    const cls = getButtonClassName({ variant: "commit", themeType });
    assert.match(cls, /\bbg-osce-commit\b/);
    assert.match(cls, /\bhover:bg-osce-commit-hover\b/);
  }
});

for (const variant of ["outline", "secondary"] as const) {
  test(`B2C ${variant} button has a brand border and fills on hover`, () => {
    const cls = getButtonClassName({ variant, themeType: "b2c" });
    assert.match(cls, /\bborder-osce-accent\b/);
    assert.match(cls, /\bhover:bg-osce-accent\b/);
  });
}
