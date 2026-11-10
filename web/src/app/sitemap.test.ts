import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";
import sitemap from "@/app/sitemap";
import { SITE_URL } from "@/app/metadata";
import { PRIVATE_PATH_PREFIXES, PUBLIC_MARKETING_PATHS } from "@/foundation/routing/pathVisibility";
import { HIDDEN_EXAM_PATHS } from "@/domains/marketing/site/siteLinks";

const realFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = realFetch;
});

/** Answers the api's media list: two pages of one post each, the second reached by cursor. */
function mockMediaApi(): string[] {
  const asked: string[] = [];
  globalThis.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    asked.push(url);
    const second = url.includes("cursor=c2");
    const post = second
      ? { slug: "second-post", updated_at: "2026-09-02T10:00:00Z" }
      : { slug: "first-post", updated_at: "2026-10-01T10:00:00Z" };
    return new Response(JSON.stringify({ items: [post], next_cursor: second ? null : "c2", total_count: 2 }), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }) as typeof fetch;
  return asked;
}

describe("sitemap", () => {
  it("lists every public marketing path except the one that canonicalises to the homepage", async () => {
    mockMediaApi();
    const urls = (await sitemap()).map((entry) => entry.url);
    for (const path of PUBLIC_MARKETING_PATHS) {
      if (path === "/exams/classic" || HIDDEN_EXAM_PATHS.includes(path)) continue;
      assert.ok(urls.includes(`${SITE_URL}${path}`), `${path} is missing`);
    }
    for (const path of HIDDEN_EXAM_PATHS) assert.ok(!urls.includes(`${SITE_URL}${path}`), `${path} is hidden`);
    assert.ok(!urls.includes(`${SITE_URL}/exams/classic`));
  });

  it("lists every published blog, walking the cursor, dated by its last update", async () => {
    const asked = mockMediaApi();
    const entries = await sitemap();
    const first = entries.find((entry) => entry.url === `${SITE_URL}/blogs/first-post`);
    const second = entries.find((entry) => entry.url === `${SITE_URL}/blogs/second-post`);
    assert.equal(new Date(first?.lastModified ?? 0).toISOString(), "2026-10-01T10:00:00.000Z");
    assert.equal(new Date(second?.lastModified ?? 0).toISOString(), "2026-09-02T10:00:00.000Z");
    assert.ok(asked[0]?.includes("limit=100") && asked[0]?.includes("kind=blog"));
  });

  it("still lists the static paths when the api is down", async () => {
    globalThis.fetch = (async () => {
      throw new TypeError("fetch failed");
    }) as typeof fetch;
    const urls = (await sitemap()).map((entry) => entry.url);
    assert.ok(urls.includes(`${SITE_URL}/pricing`));
    assert.ok(urls.includes(`${SITE_URL}/blogs`));
    assert.ok(!urls.some((url) => url.includes("/blogs/")));
  });

  it("lists no private path", async () => {
    mockMediaApi();
    for (const entry of await sitemap()) {
      const path = entry.url.slice(SITE_URL.length);
      for (const prefix of PRIVATE_PATH_PREFIXES) {
        assert.ok(!(path + "/").startsWith(prefix) && path !== prefix, `${path} is private`);
      }
    }
  });
});
