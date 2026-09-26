import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { robotsFor } from "@/app/robots";
import { PRIVATE_PATH_PREFIXES } from "@/foundation/routing/pathVisibility";

describe("robotsFor", () => {
  it("allows the marketing surface and disallows the private prefixes on production", () => {
    assert.deepEqual(robotsFor("https://osceguide.com"), {
      rules: {
        userAgent: "*",
        allow: "/",
        disallow: [...PRIVATE_PATH_PREFIXES],
      },
      sitemap: "https://osceguide.com/sitemap.xml",
    });
  });

  it("disallows everything on staging", () => {
    assert.deepEqual(robotsFor("https://staging.osceguide.com"), {
      rules: { userAgent: "*", disallow: "/" },
    });
  });

  it("disallows everything on a Vercel preview", () => {
    assert.deepEqual(robotsFor("https://my-branch-osce.vercel.app"), {
      rules: { userAgent: "*", disallow: "/" },
    });
  });
});
