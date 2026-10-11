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
  test(`B2C ${variant} button is a neutral bordered button`, () => {
    const cls = getButtonClassName({ variant, themeType: "b2c" });
    assert.match(cls, /\bborder-b2c-border\b/);
    assert.match(cls, /\btext-osce-ink-900\b/);
    assert.match(cls, /\bhover:bg-b2c-secondary\b/);
    assert.doesNotMatch(cls, /border-osce-accent|hover:bg-osce-accent|text-osce-accent|hover:!text-white/);
  });
}
