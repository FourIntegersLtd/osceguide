import assert from "node:assert/strict";
import { test } from "node:test";
import { showCameraLine } from "./sideTabPreference";

test("camera line: needs the camera, and shows when collapsed or the Covered tab is active", () => {
  assert.equal(showCameraLine({ cameraOn: false, collapsed: true, tab: "covered" }), false);
  assert.equal(showCameraLine({ cameraOn: true, collapsed: true, tab: "cues" }), true);
  assert.equal(showCameraLine({ cameraOn: true, collapsed: false, tab: "covered" }), true);
  assert.equal(showCameraLine({ cameraOn: true, collapsed: false, tab: "cues" }), false);
});
