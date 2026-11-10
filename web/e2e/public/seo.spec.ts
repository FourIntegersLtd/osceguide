import { expect, test } from "@playwright/test";
import { PUBLIC_MARKETING_PATHS } from "../../src/foundation/routing/pathVisibility";

/**
 * What a crawler receives: the raw HTML of every public page, with no
 * JavaScript run. Search Console showed one indexed page because every page
 * canonicalised to the homepage and the homepage was a spinner; these asserts
 * keep that from coming back. `request` fetches the HTML and runs nothing.
 *
 * `/exams/classic` renders the same page as `/`, so its canonical is `/` and it
 * shares the homepage's title.
 */
const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL?.trim() || "https://osceguide.com").replace(/\/+$/, "");
const SAME_AS_HOME = "/exams/classic";
// /pricing is a price table with little prose, and /blogs on a fresh database (CI) lists no posts yet: both get a lower floor. /feedback is a form with little prose, so it gets a floor with margin.
const WORD_FLOOR: Record<string, number> = { "/pricing": 25, "/blogs": 25, "/feedback": 80 };
const DEFAULT_WORD_FLOOR = 150;

function tag(html: string, pattern: RegExp): string {
  return (html.match(pattern)?.[1] ?? "").trim();
}

function visibleWords(html: string): number {
  const body = html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&[a-z#0-9]+;/gi, " ");
  return body.split(/\s+/).filter((word) => /[\p{L}\p{N}]/u.test(word)).length;
}

const titles = new Map<string, string>();

test.describe("public pages as a crawler sees them", () => {
  for (const path of PUBLIC_MARKETING_PATHS) {
    test(`SEO ${path || "/"}`, async ({ request }) => {
      const response = await request.get(path || "/", { headers: { "user-agent": "Googlebot" } });
      expect(response.status()).toBe(200);
      const html = await response.text();

      const expectedCanonical = path === SAME_AS_HOME ? SITE_URL : `${SITE_URL}${path}`;
      expect(tag(html, /<link[^>]*rel="canonical"[^>]*href="([^"]*)"/i)).toBe(expectedCanonical);
      expect(tag(html, /<meta[^>]*name="description"[^>]*content="([^"]*)"/i).length).toBeGreaterThan(0);

      const title = tag(html, /<title[^>]*>([\s\S]*?)<\/title>/i);
      expect(title).not.toContain("OSCE Guide | OSCE Guide");
      if (path !== SAME_AS_HOME) {
        expect(titles.get(title), `${path} repeats the title of ${titles.get(title)}`).toBeUndefined();
        titles.set(title, path || "/");
      }

      expect((html.match(/<h1[\s>]/gi) ?? []).length).toBe(1);
      expect(visibleWords(html)).toBeGreaterThanOrEqual(WORD_FLOOR[path] ?? DEFAULT_WORD_FLOOR);
    });
  }
});

/**
 * One real published post, found through the api, as a crawler gets it: its
 * own title, description and canonical, a single h1, the body in the HTML and
 * BlogPosting structured data.
 */
test("SEO a blog post", async ({ request }) => {
  const list = await request.get("/api/v1/media?kind=blog&limit=24&sort=published");
  const items = list.ok()
    ? ((await list.json()) as { items: { slug: string; title: string; content?: { body_md?: string } }[] }).items
    : [];
  // A real article: the short placeholder posts a dev database holds are not one.
  const post = items.find((item) => (item.content?.body_md ?? "").split(/\s+/).length >= DEFAULT_WORD_FLOOR);
  test.skip(!post, "no published blog post with a full-length body to check");
  if (!post) return;

  const response = await request.get(`/blogs/${post.slug}`, { headers: { "user-agent": "Googlebot" } });
  expect(response.status()).toBe(200);
  const html = await response.text();

  expect(tag(html, /<link[^>]*rel="canonical"[^>]*href="([^"]*)"/i)).toBe(`${SITE_URL}/blogs/${post.slug}`);
  expect(tag(html, /<title[^>]*>([\s\S]*?)<\/title>/i)).toContain(post.title);
  expect(tag(html, /<meta[^>]*name="description"[^>]*content="([^"]*)"/i).length).toBeGreaterThan(0);
  expect((html.match(/<h1[\s>]/gi) ?? []).length).toBe(1);
  expect(visibleWords(html)).toBeGreaterThanOrEqual(DEFAULT_WORD_FLOOR);

  const jsonLd = [...html.matchAll(/<script[^>]*application\/ld\+json[^>]*>([\s\S]*?)<\/script>/gi)].map((m) => m[1] ?? "");
  expect(jsonLd.some((block) => block.includes('"BlogPosting"') && block.includes(post.title))).toBe(true);
});

// The root `loading.tsx` streams the shell first, so Googlebot gets 200 with the
// not-found page's `noindex` rather than a 404 status: assert what it can act on.
test("SEO a missing blog post is not indexable", async ({ request }) => {
  const response = await request.get("/blogs/no-such-post-anywhere", { headers: { "user-agent": "Googlebot" } });
  const html = await response.text();
  expect(response.status() === 404 || /<meta[^>]*name="robots"[^>]*noindex/i.test(html)).toBe(true);
  expect(html).not.toContain('"BlogPosting"');
});
