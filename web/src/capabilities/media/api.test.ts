import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { audioUrl, podcastSeries, type MediaItem } from "@/capabilities/media/api";

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
