import assert from "node:assert/strict";
import { test } from "node:test";
import { parseTab, tabFooter } from "@/capabilities/authoring/rubrics/schemeTabs";

test("an unknown or missing tab is the first tab", () => {
  assert.equal(parseTab(null), "domains");
  assert.equal(parseTab("nonsense"), "domains");
  assert.equal(parseTab("pass"), "pass");
});

test("the footer names the tab each button goes to", () => {
  const scale = tabFooter("scale");
  assert.equal(scale.where, "Step 2 of 6: Scale");
  assert.equal(scale.backLabel, "Back: Domains");
  assert.equal(scale.nextLabel, "Next: Pass rule");
  assert.equal(tabFooter("domains").back, null);
});

test("the last step offers Publish and Versions sits outside the steps", () => {
  const trial = tabFooter("trial");
  assert.equal(trial.next, null);
  assert.equal(trial.nextLabel, "Publish");
  const versions = tabFooter("versions");
  assert.equal(versions.where, "Versions is outside the steps");
  assert.equal(versions.backLabel, "Back to the steps: Domains");
  assert.equal(versions.back, "domains");
});
