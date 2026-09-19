/**
 * The product arms, named once.
 *
 * A surface is where a person is standing, not what they bought. The backend
 * has no notion of arms — it has exams, organisations with programmes,
 * entitlements and one `attempts` table — so a surface is purely a frontend
 * shape over those, and nothing below this tier is allowed to branch on one.
 */
export const SURFACES = ["train", "assess", "hire", "platform"] as const;

export type Surface = (typeof SURFACES)[number];

export const SURFACE_LABELS: Record<Surface, string> = {
  train: "Practice",
  assess: "Institution",
  hire: "Hiring",
  platform: "OSCE Guide",
};

/**
 * The assistant backend spells surfaces its own way
 * (`assistant_content/request.py`), and that wire vocabulary is fixed by the
 * content packs keyed on it. Mapping here rather than renaming the arms keeps
 * one translation in one place — the same discipline the backend applies to
 * `athena-doctor` / `consulting-doctor`.
 */
export type AssistantSurface = "exam" | "admin" | "employer";

const ASSISTANT_SURFACE: Record<Surface, AssistantSurface> = {
  train: "exam",
  assess: "admin",
  hire: "employer",
  // The staff console reads as an admin surface to the content packs; there is
  // no fourth pack and inventing one would return empty help.
  platform: "admin",
};

export function assistantSurfaceFor(surface: Surface): AssistantSurface {
  return ASSISTANT_SURFACE[surface];
}

/**
 * Where a surface's routes live.
 *
 * Capabilities declare a path *relative* to this, so the same help capability
 * is `/help` on Train and `/assess/kings/help` on Assess without knowing that
 * either spelling exists.
 */
export function surfaceBasePath(surface: Surface, orgSlug?: string | null): string {
  switch (surface) {
    case "train":
      return "";
    case "assess":
      return orgSlug ? `/assess/${orgSlug}` : "/assess";
    case "hire":
      return orgSlug ? `/hire/${orgSlug}` : "/hire";
    case "platform":
      return "/platform";
  }
}

export function isSurface(value: string): value is Surface {
  return (SURFACES as readonly string[]).includes(value);
}
