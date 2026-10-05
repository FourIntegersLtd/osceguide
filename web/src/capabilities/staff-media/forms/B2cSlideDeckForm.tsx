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
import {
  Badge,
  Button,
  Input,
  Select,
  Textarea,
  type BadgeTone,
  FoldSection,
} from "@/foundation/ui";
import {
  HiOutlineArrowDown,
  HiOutlineArrowUp,
  HiOutlinePlus,
  HiOutlineTrash,
} from "react-icons/hi2";
import { AuthoringIconAction } from "@/capabilities/authoring/parts/AuthoringIconAction";

function statusTone(status: string): BadgeTone {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (isAvRunning(status)) return "accent";
  return "warning";
}

export function B2cSlideDeckForm({
  content,
  onChange,
}: {
  content: Record<string, unknown>;
  onChange: (content: Record<string, unknown>) => void;
}) {
  const slides = slidesFromContent(content);
  const status = avStatus(content) ?? "completed";

  const patch = (partial: Record<string, unknown>) =>
    onChange(mergeContent(content, partial));

  const updateSlides = (next: B2cSlide[]) =>
    onChange(setSlides(content, renumberSlidePositions(next)));

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
        <Badge tone={statusTone(status)}>{status.replace(/_/g, " ")}</Badge>
      </div>

      <Input
        label="Topic"
        value={typeof content.topic === "string" ? content.topic : ""}
        onChange={(e) => patch({ topic: e.target.value })}
      />
      <Select
        label="Specialty"
        value={typeof content.specialty === "string" ? content.specialty : ""}
        onChange={(e) => patch({ specialty: e.target.value })}
      >
        <option value="">-</option>
        {MEDICAL_SPECIALTY_NAMES.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </Select>
      <Input
        label="Final video URL"
        value={
          typeof content.final_video_url === "string"
            ? content.final_video_url
            : typeof content.video_url === "string"
              ? content.video_url
              : ""
        }
        onChange={(e) =>
          patch({ final_video_url: e.target.value, video_url: e.target.value })
        }
      />

      <div className="flex items-center justify-between gap-2">
        <h3 className="text-osce-subheading font-semibold text-ink">Slides</h3>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          className="gap-1"
          onClick={() =>
            updateSlides([...slides, emptyB2cSlide(slides.length + 1)])
          }
        >
          <HiOutlinePlus className="h-4 w-4" aria-hidden />
          Add slide
        </Button>
      </div>

      <ul className="flex flex-col gap-4">
        {slides.map((slide, index) => (
          <li key={index}>
            <FoldSection
              number={index + 1}
              title={slide.title?.trim() || "Untitled slide"}
              actions={
                <>
                <AuthoringIconAction
                  variant="ghost"
                  label="Move up"
                  disabled={index === 0}
                  onClick={() => updateSlides(moveSlide(slides, index, -1))}
                >
                  <HiOutlineArrowUp className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
                <AuthoringIconAction
                  variant="ghost"
                  label="Move down"
                  disabled={index === slides.length - 1}
                  onClick={() => updateSlides(moveSlide(slides, index, 1))}
                >
                  <HiOutlineArrowDown className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
                <AuthoringIconAction
                  variant="ghost"
                  label="Remove slide"
                  onClick={() => updateSlides(slides.filter((_, i) => i !== index))}
                >
                  <HiOutlineTrash className="h-4 w-4" aria-hidden />
                </AuthoringIconAction>
              </>
              }
            >
            <div className="flex flex-col gap-3">
              <Input
                label="Position"
                type="number"
                value={String(slide.position ?? index + 1)}
                onChange={(e) =>
                  updateSlide(index, {
                    position: Number(e.target.value) || index + 1,
                  })
                }
              />
              <Input
                label="Title"
                value={slide.title ?? ""}
                onChange={(e) => updateSlide(index, { title: e.target.value })}
              />
              <Select
                label="Layout"
                value={slide.layout ?? "text_only"}
                onChange={(e) => updateSlide(index, { layout: e.target.value })}
              >
                {SLIDE_LAYOUTS.map((layout) => (
                  <option key={layout} value={layout}>
                    {layout}
                  </option>
                ))}
              </Select>
              <StringListField
                label="Bullet points"
                items={bulletsAsStrings(slide)}
                onChange={(items) => setBullets(index, items)}
              />
              <Textarea
                label="Explanation / answer"
                value={slide.explanation ?? ""}
                onChange={(e) =>
                  updateSlide(index, { explanation: e.target.value })
                }
              />
              <Textarea
                label="Speaker notes (TTS)"
                value={slide.speaker_notes ?? ""}
                onChange={(e) =>
                  updateSlide(index, { speaker_notes: e.target.value })
                }
              />
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
              {slide.image_urls?.length ? (
                <div className="flex flex-wrap gap-3">
                  {slide.image_urls.map((url, picture) => {
                    const credit = slide.image_credits?.[picture];
                    return (
                      <figure key={url} className="flex w-40 flex-col gap-1">
                        {/* eslint-disable-next-line @next/next/no-img-element -- a stored picture at its own URL */}
                        <img
                          src={url}
                          alt={`Slide ${index + 1}, ${picture + 1} of ${slide.image_urls?.length ?? 1}`}
                          className="aspect-video w-full rounded-osce-md border border-border object-cover"
                        />
                        {credit?.author || credit?.licence ? (
                          <figcaption className="text-osce-caption text-ink-subtle">
                            {[credit.author, credit.licence].filter(Boolean).join(", ")}
                          </figcaption>
                        ) : null}
                      </figure>
                    );
                  })}
                </div>
              ) : null}
            </div>
            </FoldSection>
          </li>
        ))}
      </ul>
    </div>
  );
}
