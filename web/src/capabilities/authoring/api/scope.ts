import type { components } from "@/foundation/platform-client";

/**
 * Everything authoring asks the backend, written once against a variable base.
 *
 * The backend serves the same shapes twice — `/orgs/{slug}/stations` and
 * `/platform/stations`, and so on for station templates, feedback templates,
 * rubrics and exams. The retiring client answered that by keeping the
 * institution's authoring, the partner's and the platform admin's as three
 * trees, and a fix to one reached the others when somebody remembered.
 *
 * So the scope is a variable, not a fork: every function below takes an
 * `AuthoringScope` and prefixes the same path with it. There is no branch on
 * the arm anywhere in this capability, which is also what lets it stay a
 * capability — see ADR 0001.
 */

export interface AuthoringScope {
  /** `/api/v1/orgs/{slug}` for a workspace, `/api/v1/platform` for staff. */
  base: string;
  kind: "org" | "platform";
}

/**
 * Where this mount is writing.
 *
 * An organisation's workspace owns its own material; the staff console writes
 * the platform catalogue. Those are the only two scopes the backend has, and
 * a partner is simply an organisation, which is why a partner needs no case.
 */
export function authoringScope(surface: string, orgSlug: string | null): AuthoringScope {
  if (orgSlug) {
    return { base: `/api/v1/orgs/${encodeURIComponent(orgSlug)}`, kind: "org" };
  }
  if (surface === "platform") return { base: "/api/v1/platform", kind: "platform" };
  // A personal workspace has nothing to author into. Asking anyway would put a
  // malformed path on the wire, so say so here instead.
  throw new Error("Authoring needs an organisation or the staff surface");
}

/* Four asymmetries in the backend, named rather than discovered at runtime.
 * `docs/port-gaps.md` carries the detail. */

/**
 * Where exams are *listed*.
 *
 * The one place the scope is not simply a prefix. `/platform/exams` is
 * POST-only: the platform's listing is the unscoped `/exams`, which already
 * answers a platform admin with the catalogue's drafts included and answers
 * everybody else without them. Writing it as a prefix put a GET on a POST-only
 * route, and the staff console's Exams section showed a 405 where the
 * catalogue should be.
 *
 * `drafts` goes with the organisation's listing only, where it narrows to that
 * institution's own rows. The platform listing decides by who is asking, so
 * passing it there would be a query the backend ignores.
 */
export function examListPath(scope: AuthoringScope): string {
  return scope.kind === "platform" ? "/api/v1/exams" : `${scope.base}/exams`;
}

/** Programmes are an institution's own grouping; the catalogue has none. */
export const supportsProgrammes = (s: AuthoringScope) => s.kind === "org";
/** `…/versions/{v}/brief` is org-only. */
export const supportsBrief = (s: AuthoringScope) => s.kind === "org";
/** Throwing a draft away is org-only; the catalogue archives instead. */
export const supportsVersionDelete = (s: AuthoringScope) => s.kind === "org";

type S = components["schemas"];

export type Station = S["StationRead"];
export type StationVersion = S["StationVersionRead"];
export type StationTemplate = S["StationTemplateRead"];
export type StationTemplateVersion = S["StationTemplateVersionRead"];
export type FeedbackTemplate = S["FeedbackTemplateRead"];
export type FeedbackTemplateVersion = S["FeedbackTemplateVersionRead"];
export type Rubric = S["RubricRead"];
export type RubricVersion = S["RubricVersionRead"];
export type Exam = S["ExamRead"];
export type Programme = S["ProgrammeRead"];

export type Json = Record<string, unknown>;

/** One place the path segments are escaped. */
export const pathId = (value: string) => encodeURIComponent(value);
