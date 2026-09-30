import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { getButtonClassName } from "./buttonStyles";

describe("getButtonClassName — the commit tier", () => {
  it("renders black at rest and darkens on hover", () => {
    const cls = getButtonClassName({ themeType: "b2c", variant: "commit" });
    // Rest sits at ink-800 so the hover has room to move: there is no usable
    // step below ink-900, so the pair lives one rung up the ramp.
    assert.match(cls, /\bbg-osce-ink-800\b/);
    assert.match(cls, /\bhover:bg-osce-ink-900\b/);
    assert.doesNotMatch(cls, /hover:bg-osce-accent\b/);
  });

  it("keeps a blue focus ring, and forces white text over LiveKit's theme vars", () => {
    const cls = getButtonClassName({ themeType: "b2c", variant: "commit" });
    assert.match(cls, /focus:ring-osce-accent\/40/);
    assert.match(cls, /!text-white/);
  });

  it("is a distinct tier from blue primary in b2c", () => {
    assert.notEqual(
      getButtonClassName({ themeType: "b2c", variant: "commit" }),
      getButtonClassName({ themeType: "b2c", variant: "primary" }),
    );
  });

  it("is the same black in b2b, and distinct from b2b's blue", () => {
    // The two arms disagree about how often black appears, not about what it
    // is: b2b makes it the default primary, b2c reserves it. One colour pair.
    const b2b = getButtonClassName({ themeType: "b2b", variant: "commit" });
    assert.match(b2b, /\bbg-osce-ink-800\b/);
    assert.match(b2b, /\bhover:bg-osce-ink-900\b/);
    assert.notEqual(b2b, getButtonClassName({ themeType: "b2b", variant: "primary" }));
  });

  it("uses one shared black across both arms", () => {
    // Sizes differ per theme, variants no longer do — compare the colour half.
    const colours = (c: string) =>
      c.split(" ").filter((x) => /(?:^|:)!?(?:bg|text|hover:bg|focus:ring)-/.test(x)).sort().join(" ");
    assert.equal(
      colours(getButtonClassName({ themeType: "b2c", variant: "commit" })),
      colours(getButtonClassName({ themeType: "b2b", variant: "commit" })),
    );
  });
});
