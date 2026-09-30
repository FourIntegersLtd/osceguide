import type { DeckSlide } from "@/capabilities/media/api";

type RawSlide = Record<string, unknown>;

function bulletLines(slide: RawSlide): string[] {
  const bullets = slide.bullets;
  if (!Array.isArray(bullets)) return [];
  return bullets
    .map((b) => {
      if (typeof b === "string") return b.trim();
      if (b && typeof b === "object" && typeof (b as { text?: string }).text === "string") {
        return (b as { text: string }).text.trim();
      }
      return "";
    })
    .filter(Boolean);
}

function bodyFromSlide(slide: RawSlide): string | undefined {
  if (typeof slide.body === "string" && slide.body.trim()) return slide.body;
  const explanation =
    typeof slide.explanation === "string" && slide.explanation.trim() ? slide.explanation : "";
  const lines = bulletLines(slide);
  if (lines.length === 0) return explanation || undefined;
  const list = lines.map((line) => `- ${line}`).join("\n");
  return explanation ? `${explanation}\n\n${list}` : list;
}

function imageFromSlide(slide: RawSlide): string | undefined {
  if (typeof slide.image_url === "string" && slide.image_url.trim()) return slide.image_url;
  const urls = slide.image_urls;
  if (Array.isArray(urls)) {
    const first = urls.find((u) => typeof u === "string" && u.trim());
    if (typeof first === "string") return first;
  }
  return undefined;
}

/** Map B2C slide JSON to the simplified shape `DeckStage` already renders. */
export function b2cDeckSlides(content: Record<string, unknown>): DeckSlide[] {
  const slides = content.slides;
  if (!Array.isArray(slides)) return [];
  return slides.map((entry) => {
    if (!entry || typeof entry !== "object") return {};
    const slide = entry as RawSlide;
    const title = typeof slide.title === "string" ? slide.title : undefined;
    const body = bodyFromSlide(slide);
    const image_url = imageFromSlide(slide);
    return { title, body, image_url };
  });
}
