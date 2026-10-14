import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { metadata, metadataRobotsFor, publicPageMetadata } from "@/app/metadata";

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

describe("publicPageMetadata", () => {
  it("gives a page its own canonical, title and description, in the head and in the share card", () => {
    assert.deepEqual(
      publicPageMetadata({ path: "/pricing", title: "Pricing", description: "Plans for every exam." }),
      {
        title: "Pricing",
        description: "Plans for every exam.",
        alternates: { canonical: "/pricing" },
        openGraph: { url: "/pricing", title: "Pricing", description: "Plans for every exam." },
      },
    );
  });

  it("canonicalises the homepage to the site root", () => {
    assert.equal(publicPageMetadata({ path: "/", title: "T", description: "D" }).alternates?.canonical, "/");
  });

  it("sets no canonical of its own on the root metadata, so a page without one is not the homepage", () => {
    assert.equal(metadata.alternates?.canonical, undefined);
    assert.equal(metadata.openGraph?.url, undefined);
  });
});
