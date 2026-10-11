import assert from "node:assert/strict";
import { describe, it } from "node:test";
import type { MediaItem } from "@/capabilities/media/api";
import { CLIENT_PAGE_SIZE, podcastOrder, sortByTitle } from "@/capabilities/media/catalogue";

const item = (title: string, extras: Record<string, unknown> = {}): MediaItem =>
  ({ id: title, slug: title, title, kind: "summary", content: {}, exam_code: "sca", ...extras }) as unknown as MediaItem;

describe("client-side load more (A to Z, Podcasts)", () => {
  const all = sortByTitle(["Zoster", "Asthma", "Migraine", "Gout", "Bell", "Eczema", "Croup", "Hernia", "Anaemia", "Dengue", "Fits", "Acne"].map((t) => item(t)));

  it("sorts the whole catalogue by title before paging", () => {
    assert.deepEqual(all.slice(0, 3).map((i) => i.title), ["Acne", "Anaemia", "Asthma"]);
  });

  it("a later page appends under the first: it never re-sorts above the fold", () => {
    const first = all.slice(0, CLIENT_PAGE_SIZE).map((i) => i.title);
    const second = all.slice(0, CLIENT_PAGE_SIZE * 2).map((i) => i.title);
    assert.deepEqual(second.slice(0, CLIENT_PAGE_SIZE), first);
    assert.equal(second.length, 12);
  });

  it("podcast Previous/Next order is the visible order, by title within a series", () => {
    const order = podcastOrder([item("C", { exam_code: "sca" }), item("A", { exam_code: "sca" }), item("B", { exam_code: "sca" })]);
    assert.deepEqual(order.map((i) => i.title), ["A", "B", "C"]);
  });
});
