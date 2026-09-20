"use client";

import type { DeckSlide } from "@/capabilities/media/api";
import { Button, Input } from "@/foundation/ui";
import { HiOutlinePlus, HiOutlineTrash } from "react-icons/hi2";

function slidesFrom(content: Record<string, unknown>): DeckSlide[] {
  const raw = content.slides;
  if (!Array.isArray(raw)) return [];
  return raw.map((entry) => {
    if (!entry || typeof entry !== "object") return {};
    const slide = entry as Record<string, unknown>;
    return {
      title: typeof slide.title === "string" ? slide.title : "",
      body: typeof slide.body === "string" ? slide.body : "",
      image_url: typeof slide.image_url === "string" ? slide.image_url : "",
    };
  });
}

export function SlideDeckContentForm({
  content,
  onChange,
}: {
  content: Record<string, unknown>;
  onChange: (content: Record<string, unknown>) => void;
}) {
  const slides = slidesFrom(content);

  const setSlides = (next: DeckSlide[]) => {
    onChange({ ...content, slides: next });
  };

  const updateSlide = (index: number, patch: Partial<DeckSlide>) => {
    const next = [...slides];
    next[index] = { ...next[index], ...patch };
    setSlides(next);
  };

  return (
    <div className="flex flex-col gap-4">
      <Input
        label="Video URL (optional)"
        value={typeof content.video_url === "string" ? content.video_url : ""}
        onChange={(e) => onChange({ ...content, video_url: e.target.value })}
      />
      <Input
        label="Final video URL (optional)"
        value={typeof content.final_video_url === "string" ? content.final_video_url : ""}
        onChange={(e) => onChange({ ...content, final_video_url: e.target.value })}
      />
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-ink">Slides</span>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          className="gap-1"
          onClick={() => setSlides([...slides, { title: "", body: "" }])}
        >
          <HiOutlinePlus className="h-4 w-4" aria-hidden />
          Add slide
        </Button>
      </div>
      <ul className="flex flex-col gap-4">
        {slides.map((slide, index) => (
          <li key={index} className="rounded-control border border-border p-4">
            <div className="mb-3 flex items-center justify-between gap-2">
              <span className="text-sm font-medium text-ink">Slide {index + 1}</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                aria-label={`Remove slide ${index + 1}`}
                onClick={() => setSlides(slides.filter((_, i) => i !== index))}
              >
                <HiOutlineTrash className="h-4 w-4" aria-hidden />
              </Button>
            </div>
            <div className="flex flex-col gap-3">
              <Input
                label="Title"
                value={slide.title ?? ""}
                onChange={(e) => updateSlide(index, { title: e.target.value })}
              />
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="font-medium text-ink">Body</span>
                <textarea
                  value={slide.body ?? ""}
                  onChange={(e) => updateSlide(index, { body: e.target.value })}
                  rows={4}
                  className="rounded-control border border-border-strong bg-surface px-3 py-2 text-sm"
                />
              </label>
              <Input
                label="Image URL"
                value={slide.image_url ?? ""}
                onChange={(e) => updateSlide(index, { image_url: e.target.value })}
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
