/** B2C-aligned study-material `content` helpers. Preserve unknown keys on merge. */

export const SLIDE_LAYOUTS = [
  "text_only",
  "text_image_right",
  "text_image_left",
  "full_image",
  "triple_image",
] as const;

export type SlideLayout = (typeof SLIDE_LAYOUTS)[number];

export type B2cSlide = {
  id?: string;
  position?: number;
  title?: string;
  bullets?: (string | { text?: string })[];
  explanation?: string | null;
  speaker_notes?: string;
  layout?: SlideLayout | string;
  has_pause?: boolean;
  pause_duration?: number;
  image_urls?: string[];
  image_url?: string;
  body?: string;
};

export type AvStatus =
  | "completed"
  | "failed"
  | "generating_audio"
  | "generating_video"
  | "generating_podcast"
  | string;

export function mergeContent(
  base: Record<string, unknown>,
  patch: Record<string, unknown>,
): Record<string, unknown> {
  return { ...base, ...patch };
}

export function patchContentField(
  content: Record<string, unknown>,
  key: string,
  value: unknown,
): Record<string, unknown> {
  return mergeContent(content, { [key]: value });
}

export function stringListField(content: Record<string, unknown>, key: string): string[] {
  const raw = content[key];
  if (!Array.isArray(raw)) return [];
  return raw.map((v) => String(v));
}

export function specialtiesFromContent(content: Record<string, unknown>): string[] {
  const many = stringListField(content, "specialties");
  if (many.length > 0) return many;
  const one = content.specialty;
  if (typeof one === "string" && one.trim()) return [one.trim()];
  return [];
}

export function setSpecialties(content: Record<string, unknown>, names: string[]): Record<string, unknown> {
  const cleaned = names.map((n) => n.trim()).filter(Boolean);
  return mergeContent(content, {
    specialties: cleaned,
    specialty: cleaned[0] ?? "",
  });
}

export function avStatus(content: Record<string, unknown>): AvStatus | null {
  const raw = content.status;
  return typeof raw === "string" && raw.trim() ? raw : null;
}

export function isAvRunning(status: AvStatus | null): boolean {
  if (!status) return false;
  return (
    status.startsWith("generating") ||
    status === "checking_facts" ||
    status === "writing_script"
  );
}

export function slidesFromContent(content: Record<string, unknown>): B2cSlide[] {
  const raw = content.slides;
  if (!Array.isArray(raw)) return [];
  return raw.map((entry, index) => {
    if (!entry || typeof entry !== "object") return { position: index + 1, title: "" };
    const slide = entry as B2cSlide;
    return {
      ...slide,
      position: slide.position ?? index + 1,
    };
  });
}

export function bulletsAsStrings(slide: B2cSlide): string[] {
  const raw = slide.bullets;
  if (!Array.isArray(raw)) return [];
  return raw.map((b) => {
    if (typeof b === "string") return b;
    if (b && typeof b === "object" && typeof b.text === "string") return b.text;
    return String(b);
  });
}

export function setSlides(content: Record<string, unknown>, slides: B2cSlide[]): Record<string, unknown> {
  return patchContentField(content, "slides", slides);
}

export function renumberSlidePositions(slides: B2cSlide[]): B2cSlide[] {
  return slides.map((s, i) => ({ ...s, position: i + 1 }));
}

export function moveSlide(slides: B2cSlide[], index: number, direction: -1 | 1): B2cSlide[] {
  const next = [...slides];
  const target = index + direction;
  if (target < 0 || target >= next.length) return slides;
  const current = next[index];
  const swap = next[target];
  if (!current || !swap) return slides;
  next[index] = swap;
  next[target] = current;
  return renumberSlidePositions(next);
}

export function emptyB2cSlide(position: number): B2cSlide {
  return {
    position,
    title: "",
    layout: "text_only",
    bullets: [],
    speaker_notes: "",
    explanation: "",
    image_urls: [],
    has_pause: false,
  };
}
