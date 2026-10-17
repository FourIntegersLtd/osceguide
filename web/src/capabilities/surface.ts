/**
 * The product arms, named once.
 *
 * A surface is where a person is standing, not what they bought. The backend
 * has no notion of arms — it has exams, organisations with a `org_type`,
 * entitlements and one `attempts` table — so a surface is purely a frontend
 * shape over those, and nothing below this tier is allowed to branch on one.
 *
 * This file holds the *names* and nothing else. Which shell an arm renders,
 * what its navigation is and which screens it owns all live in
 * `src/surfaces/registry.ts`, one tier up. The split is what lets a capability
 * know the name of the surface it is mounted on without being able to import a
 * surface — the rule ADR 0001 exists to enforce.
 */
export const SURFACES = ["train", "assess", "hire", "partner", "platform"] as const;

export type Surface = (typeof SURFACES)[number];

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
  // A partner authors content for the platform, so the admin pack is the one
  // that knows the vocabulary they are asking about.
  partner: "admin",
  // The staff console reads as an admin surface to the content packs; there is
  // no fourth pack and inventing one would return empty help.
  platform: "admin",
};

export function assistantSurfaceFor(surface: Surface): AssistantSurface {
  return ASSISTANT_SURFACE[surface];
}

export function isSurface(value: string): value is Surface {
  return (SURFACES as readonly string[]).includes(value);
}

/** An institution's, employer's or partner's workspace: access is arranged by an administrator, never bought. */
export const isOrgSurface = (surface: string): boolean => surface === "assess" || surface === "hire" || surface === "partner";

/** Athena is the consumer's tutor and the staff console's helper; an institution, employer or partner never sees her. */
export const athenaOffered = (surface: string): boolean => !isOrgSurface(surface);
