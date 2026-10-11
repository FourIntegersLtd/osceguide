import assert from "node:assert/strict";
import { test } from "node:test";
import { getButtonClassName } from "./buttonStyles";

for (const variant of ["outline", "secondary"] as const) {
  test(`B2C ${variant} button has a brand border and fills on hover`, () => {
    const cls = getButtonClassName({ variant, themeType: "b2c" });
    assert.match(cls, /\bborder-osce-accent\b/);
    assert.match(cls, /\bhover:bg-osce-accent\b/);
  });
}
