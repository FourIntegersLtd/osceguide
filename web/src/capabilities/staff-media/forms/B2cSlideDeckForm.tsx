"use client";

import {
  SLIDE_LAYOUTS,
  avStatus,
  bulletsAsStrings,
  emptyB2cSlide,
  isAvRunning,
  mergeContent,
  moveSlide,
  renumberSlidePositions,
  setSlides,
  slidesFromContent,
  type B2cSlide,
} from "@/capabilities/staff-media/content/b2cMediaShapes";
import { MEDICAL_SPECIALTY_NAMES } from "@/capabilities/staff-media/content/medicalSpecialties";
import { StringListField } from "@/capabilities/staff-media/forms/StringListField";
import { Button, Input } from "@/foundation/ui";
import { cn } from "@/foundation/ui/cn";
import { b2cTableCellText } from "@/foundation/ui/productTokens";
import { HiOutlineArrowDown, HiOutlineArrowUp, HiOutlinePlus, HiOutlineTrash } from "react-icons/hi2";

function statusPillClass(status: string): string {
  if (status === "completed") return "bg-osce-success-bg text-osce-success-text";
  if (status === "failed") return "bg-osce-danger-bg text-osce-danger-text";
  if (status.startsWith("generating")) return "bg-osce-accent-subtle text-osce-accent";
  return "bg-osce-warning-bg text-osce-warning-text";
}

export function B2cSlideDeckForm({
  content,
  onChange,
  onRegenerateAv,
  avBusy,
}: {
  content: Record<string, unknown>;
  onChange: (content: Record<string, unknown>) => void;
  onRegenerateAv?: () => void;
  avBusy?: boolean;
}) {
  const slides = slidesFromContent(content);
  const status = avStatus(content) ?? "completed";

  const patch = (partial: Record<string, unknown>) => onChange(mergeContent(content, partial));

  const updateSlides = (next: B2cSlide[]) => onChange(setSlides(content, renumberSlidePositions(next)));

  const updateSlide = (index: number, partial: Partial<B2cSlide>) => {
    const next = [...slides];
    next[index] = { ...next[index], ...partial };
    updateSlides(next);
  };

  const setBullets = (index: number, lines: string[]) => {
    updateSlide(index, { bullets: lines });
  };

  const setImageUrls = (index: number, urls: string[]) => {
    updateSlide(index, { image_urls: urls.filter((u) => u.trim()) });
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span
          className={cn(
            "rounded-full px-3 py-1 font-medium capitalize",
            b2cTableCellText,
            statusPillClass(status),
          )}
        >
          {status.replace(/_/g, " ")}
        </span>
        {onRegenerateAv ? (
          <Button
            type="button"
            size="sm"
            variant="secondary"
            disabled={avBusy || isAvRunning(status)}
            onClick={onRegenerateAv}
          >
            {avBusy || isAvRunning(status) ? "Regenerating…" : "Regenerate audio & video"}
          </Button>
        ) : null}
      </div>

      <Input
        label="Topic"
        value={typeof content.topic === "string" ? content.topic : ""}
        onChange={(e) => patch({ topic: e.target.value })}
      />
      <label className="flex flex-col gap-1.5 text-sm">
        <span className="font-medium text-ink">Specialty</span>
        <select
          value={typeof content.specialty === "string" ? content.specialty : ""}
          onChange={(e) => patch({ specialty: e.target.value })}
          className="rounded-control border border-border-strong bg-surface px-3 py-2 text-sm"
        >
          <option value="">—</option>
          {MEDICAL_SPECIALTY_NAMES.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
      </label>
      <Input
        label="Final video URL"
        value={
          typeof content.final_video_url === "string"
            ? content.final_video_url
            : typeof content.video_url === "string"
              ? content.video_url
              : ""
        }
        onChange={(e) => patch({ final_video_url: e.target.value, video_url: e.target.value })}
      />

      <div className="flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-ink">Slides</h3>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          className="gap-1"
          onClick={() => updateSlides([...slides, emptyB2cSlide(slides.length + 1)])}
        >
          <HiOutlinePlus className="h-4 w-4" aria-hidden />
          Add slide
        </Button>
      </div>

      <ul className="flex flex-col gap-4">
        {slides.map((slide, index) => (
          <li key={index} className="rounded-control border border-border p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <span className="text-sm font-medium text-ink">Slide {index + 1}</span>
              <div className="flex flex-wrap gap-1">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label="Move up"
                  disabled={index === 0}
                  onClick={() => updateSlides(moveSlide(slides, index, -1))}
                >
                  <HiOutlineArrowUp className="h-4 w-4" aria-hidden />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label="Move down"
                  disabled={index === slides.length - 1}
                  onClick={() => updateSlides(moveSlide(slides, index, 1))}
                >
                  <HiOutlineArrowDown className="h-4 w-4" aria-hidden />
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  aria-label="Remove slide"
                  onClick={() => updateSlides(slides.filter((_, i) => i !== index))}
                >
                  <HiOutlineTrash className="h-4 w-4" aria-hidden />
                </Button>
              </div>
            </div>
            <div className="flex flex-col gap-3">
              <Input
                label="Position"
                type="number"
                value={String(slide.position ?? index + 1)}
                onChange={(e) => updateSlide(index, { position: Number(e.target.value) || index + 1 })}
              />
              <Input
                label="Title"
                value={slide.title ?? ""}
                onChange={(e) => updateSlide(index, { title: e.target.value })}
              />
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="font-medium text-ink">Layout</span>
                <select
                  value={slide.layout ?? "text_only"}
                  onChange={(e) => updateSlide(index, { layout: e.target.value })}
                  className="rounded-control border border-border-strong bg-surface px-3 py-2 text-sm"
                >
                  {SLIDE_LAYOUTS.map((layout) => (
                    <option key={layout} value={layout}>{layout}</option>
                  ))}
                </select>
              </label>
              <StringListField
                label="Bullet points"
                items={bulletsAsStrings(slide)}
                onChange={(items) => setBullets(index, items)}
              />
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="font-medium text-ink">Explanation / answer</span>
                <textarea
                  value={slide.explanation ?? ""}
                  onChange={(e) => updateSlide(index, { explanation: e.target.value })}
                  rows={3}
                  className="rounded-control border border-border-strong bg-surface px-3 py-2 text-sm"
                />
              </label>
              <label className="flex flex-col gap-1.5 text-sm">
                <span className="font-medium text-ink">Speaker notes (TTS)</span>
                <textarea
                  value={slide.speaker_notes ?? ""}
                  onChange={(e) => updateSlide(index, { speaker_notes: e.target.value })}
                  rows={3}
                  className="rounded-control border border-border-strong bg-surface px-3 py-2 text-sm"
                />
              </label>
              <StringListField
                label="Image URLs"
                items={
                  Array.isArray(slide.image_urls)
                    ? slide.image_urls.map(String)
                    : slide.image_url
                      ? [slide.image_url]
                      : []
                }
                onChange={(urls) => setImageUrls(index, urls)}
                placeholder="https://…"
              />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
