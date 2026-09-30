import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { cardLinkFor } from "@/capabilities/help/refRoutes";

const hrefFor = (path: string) => `/app/me${path}`;

describe("where a card Athena showed opens", () => {
  it("opens a station at its library page, by station id rather than version", () => {
    assert.deepEqual(cardLinkFor({ kind: "station", id: "version-1", slug: "station-1" }, { hrefFor }), {
      eyebrow: "Station",
      label: "Open the station",
      href: "/app/me/stations/station-1",
    });
  });

  it("falls back to the library for a station card with no station id", () => {
    assert.equal(cardLinkFor({ kind: "station", id: "version-1", slug: null }, { hrefFor })?.href, "/app/me/stations");
  });

  it("opens each kind of reading on its own tab", () => {
    const href = (kind: string, slug: string) => cardLinkFor({ kind, id: "x", slug }, { hrefFor })?.href;
    assert.equal(href("summary", "asthma"), "/app/me/library/asthma");
    assert.equal(href("blog", "a-day-in-sca"), "/app/me/library/a-day-in-sca");
    assert.equal(href("slide_deck", "copd"), "/app/me/slides?deck=copd");
    assert.equal(href("podcast", "ep-1"), "/app/me/podcast?episode=ep-1");
  });

  it("opens a help article in the dock, and not at all where there is no dock", () => {
    const opened: string[] = [];
    const link = cardLinkFor(
      { kind: "help", id: "first-steps", slug: "first-steps" },
      { hrefFor, openHelpArticle: (slug) => opened.push(slug) },
    );
    link?.onOpen?.();
    assert.deepEqual(opened, ["first-steps"]);
    assert.equal(link?.href, undefined);
    assert.equal(cardLinkFor({ kind: "help", id: "first-steps", slug: "first-steps" }, { hrefFor }), null);
  });

  it("draws no link for a kind this build has never seen", () => {
    assert.equal(cardLinkFor({ kind: "hologram", id: "x", slug: "y" }, { hrefFor }), null);
  });
});
