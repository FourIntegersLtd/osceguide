import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { audioUrl, deckCaptionsSrc, deckHeading, podcastSeries, specialtiesOf, type MediaItem } from "@/capabilities/media/api";

function episode(
  id: string,
  title: string,
  extras: { audio?: string; exam?: string | null; content?: Record<string, unknown> | null } = {},
): MediaItem {
  const content =
    extras.content !== undefined
      ? extras.content
      : extras.audio
        ? { audio_url: extras.audio }
        : {};
  return {
    id,
    kind: "podcast",
    slug: id,
    title,
    summary: null,
    content,
    exam_code: extras.exam === undefined ? "sca" : extras.exam,
    status: "published",
    created_at: "2026-09-19T00:00:00Z",
    published_at: "2026-09-19T00:00:00Z",
  } as MediaItem;
}

describe("podcastSeries", () => {
  it("keeps the page item's audio when the listing stripped the body", () => {
    const page = episode("vit-d", "Vitamin D Deficiency", {
      audio: "https://cdn.example.com/vitamin_d_deficiency.mp3",
    });
    const listed = [
      episode("seed", "Debriefing a station you think went badly"),
      episode("vit-d", "Vitamin D Deficiency", { content: null }),
    ];

    const series = podcastSeries(listed, page, "sca");
    assert.equal(series.length, 1);
    assert.equal(series[0]?.id, "vit-d");
    assert.equal(audioUrl(series[0]!), "https://cdn.example.com/vitamin_d_deficiency.mp3");
  });

  it("drops silent rows and still includes a page item the cursor missed", () => {
    const page = episode("missed", "Episode 101", { audio: "https://cdn.example.com/101.mp3" });
    const listed = [
      episode("a", "Episode A", { audio: "https://cdn.example.com/a.mp3" }),
      episode("seed", "No audio"),
    ];

    const series = podcastSeries(listed, page, "sca");
    assert.deepEqual(
      series.map((entry) => entry.id),
      ["missed", "a"],
    );
  });
});

describe("specialtiesOf", () => {
  const item = (over: Partial<MediaItem>): MediaItem =>
    ({ ...episode("s1", "Chest pain"), kind: "summary", ...over }) as MediaItem;

  it("keeps a locked item on the facet list through the root column", () => {
    // The server withholds `content` for a reader without the exam but still
    // derives `specialty`; reading the document alone dropped these items.
    assert.deepEqual(specialtiesOf(item({ content: null, locked: true, specialty: "Cardiology" })), [
      "Cardiology",
    ]);
  });

  it("prefers the document's whole list when the body is readable", () => {
    const readable = item({
      content: { specialties: ["Cardiology", "Respiratory"] },
      specialty: "Cardiology",
    });
    assert.deepEqual(specialtiesOf(readable), ["Cardiology", "Respiratory"]);
  });

  it("files nothing when neither carries one", () => {
    assert.deepEqual(specialtiesOf(item({ content: {}, specialty: null })), []);
  });
});

describe("deckHeading", () => {
  const deck = (title: string, content: Record<string, unknown>) => episode("d", title, { content });

  it("names a deck by its topic with the title beneath", () => {
    assert.deepEqual(deckHeading(deck("Case 12 telephone review", { topic: "Myeloma" })), {
      title: "Myeloma",
      subtitle: "Case 12 telephone review",
    });
  });

  it("has no subtitle when the topic is the title or is missing", () => {
    assert.deepEqual(deckHeading(deck("Myeloma", { topic: "Myeloma" })), { title: "Myeloma", subtitle: null });
    assert.deepEqual(deckHeading(deck("Myeloma", { topic: "  " })), { title: "Myeloma", subtitle: null });
  });
});

describe("deckCaptionsSrc", () => {
  it("wraps the stored track in a data URL and gives none for a deck without one", () => {
    const src = deckCaptionsSrc(episode("d", "Deck", { content: { captions_vtt: "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHi\n" } }));
    assert.equal(
      src,
      "data:text/vtt;charset=utf-8,WEBVTT%0A%0A00%3A00%3A01.000%20--%3E%2000%3A00%3A02.000%0AHi%0A",
    );
    assert.equal(deckCaptionsSrc(episode("d", "Deck", { content: {} })), null);
  });
});
