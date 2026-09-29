import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import { listExams } from "@/capabilities/authoring/api/catalog";
import {
  authoringScope,
  examListPath,
  supportsBrief,
  supportsProgrammes,
  supportsPromptGeneration,
  supportsVersionDelete,
} from "@/capabilities/authoring/api/scope";

/**
 * The claim this capability makes, pinned.
 *
 * If a fourth arm ever needs authoring, it adds no case here — it either has a
 * workspace or it is the staff console. A test that failed the moment somebody
 * added `if (surface === "partner")` is the cheapest guard there is.
 */
describe("authoring scope", () => {
  it("takes an organisation's base from its slug, whatever the arm", () => {
    for (const surface of ["assess", "partner", "hire", "platform"]) {
      assert.deepEqual(authoringScope(surface, "kings"), {
        base: "/api/v1/orgs/kings",
        kind: "org",
      });
    }
  });

  it("escapes a slug rather than pasting it into a path", () => {
    assert.equal(authoringScope("assess", "a b/c").base, "/api/v1/orgs/a%20b%2Fc");
  });

  it("writes the platform catalogue on the staff surface", () => {
    assert.deepEqual(authoringScope("platform", null), {
      base: "/api/v1/platform",
      kind: "platform",
    });
  });

  it("refuses a personal workspace, which has nothing to author into", () => {
    assert.throws(() => authoringScope("train", null));
  });

  it("names the three things only an organisation's scope serves", () => {
    const org = authoringScope("assess", "kings");
    const platform = authoringScope("platform", null);
    for (const supports of [supportsProgrammes, supportsBrief, supportsVersionDelete]) {
      assert.equal(supports(org), true);
      assert.equal(supports(platform), false);
    }
  });

  it("names the one thing only the platform's scope serves", () => {
    // Prompt-only drafting is the catalogue's, so an institution must not be
    // offered it: the route answers PlatformAdmin and would 403 on click.
    assert.equal(supportsPromptGeneration(authoringScope("platform", null)), true);
    assert.equal(supportsPromptGeneration(authoringScope("assess", "kings")), false);
  });
});

describe("the exam listing", () => {
  it("is the platform's scoped list for staff", () => {
    assert.equal(examListPath(authoringScope("platform", null)), "/api/v1/platform/exams");
  });

  it("is the organisation's own for a workspace", () => {
    assert.equal(examListPath(authoringScope("assess", "kings")), "/api/v1/orgs/kings/exams");
  });
});

describe("the platform exam listing before the scoped read is deployed", () => {
  const realFetch = globalThis.fetch;
  afterEach(() => {
    globalThis.fetch = realFetch;
  });

  it("falls back to the unscoped catalogue when /platform/exams refuses a GET", async () => {
    const seen: string[] = [];
    globalThis.fetch = (async (input: RequestInfo | URL) => {
      const url = String(input);
      seen.push(url);
      return url.includes("/platform/exams")
        ? new Response(JSON.stringify({ detail: "Method Not Allowed" }), { status: 405 })
        : new Response(JSON.stringify({ items: [], next_cursor: null }), { status: 200 });
    }) as typeof fetch;
    const page = await listExams(authoringScope("platform", null));
    assert.deepEqual(page.items, []);
    assert.deepEqual(
      seen.map((url) => url.replace(/^https?:\/\/[^/]+/, "")),
      ["/api/v1/platform/exams", "/api/v1/exams"],
    );
  });

  it("does not fall back for an organisation", async () => {
    globalThis.fetch = (async () =>
      new Response(JSON.stringify({ detail: "Not Found" }), { status: 404 })) as typeof fetch;
    await assert.rejects(() => listExams(authoringScope("assess", "kings")));
  });
});
