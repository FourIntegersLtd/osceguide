import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { formatBytes } from "@/domains/platform/support/size";

describe("formatBytes", () => {
  it("reads sizes the way the 500 MB budget is written", () => {
    assert.equal(formatBytes(812), "812 B");
    assert.equal(formatBytes(305 * 1024 * 1024), "305 MB");
    assert.equal(formatBytes(1.5 * 1024 * 1024 * 1024), "1.5 GB");
    assert.equal(formatBytes(2.5 * 1024 * 1024), "2.5 MB");
  });
});
