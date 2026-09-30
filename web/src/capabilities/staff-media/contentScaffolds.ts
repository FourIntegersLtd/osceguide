import type { MediaKind } from "@/capabilities/media/api";

export function emptyContentForKind(kind: MediaKind): Record<string, unknown> {
  switch (kind) {
    case "summary":
      return {
        red_flags: [],
        examinations: [],
        brief_management: [],
        psychosocial_aspects: [],
      };
    case "blog":
      return { body_md: "" };
    case "slide_deck":
      return { topic: "", specialty: "", slides: [], status: "completed" };
    case "podcast":
      return { audio_url: "" };
    default:
      return {};
  }
}
