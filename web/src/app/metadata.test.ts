import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { metadataRobotsFor } from "@/app/metadata";

describe("metadataRobotsFor", () => {
  it("indexes fully on production", () => {
    assert.deepEqual(metadataRobotsFor("https://osceguide.com"), {
      index: true,
      follow: true,
      googleBot: { index: true, follow: true, "max-image-preview": "large" },
    });
  });

  it("sets noindex/nofollow on staging", () => {
    assert.deepEqual(metadataRobotsFor("https://staging.osceguide.com"), {
      index: false,
      follow: false,
      googleBot: { index: false, follow: false },
    });
  });

  it("sets noindex/nofollow on a Vercel preview", () => {
    assert.deepEqual(metadataRobotsFor("https://my-branch-osce.vercel.app"), {
      index: false,
      follow: false,
      googleBot: { index: false, follow: false },
    });
  });
});
