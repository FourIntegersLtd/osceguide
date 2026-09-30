import type { components } from "@/foundation/platform-client";
import { asRatingValue, isEnumerated, ratingFraction, type Rating, type RatingValue } from "@/capabilities/feedback/rubric";

/**
 * The review form a marker fills in, read off the station's rubric.
 *
 * `ReviewFormRead` lists every path a reviewer may rate (`tasks.safety_net.score`,
 * `tasks.score`, `competent` in place of `score` on a boolean rubric), the one
 * rating those paths take and which domains must be rated before a review can
 * be completed. So the examiner's and the GP lead's forms are generated from
 * the rubric: no list of domains or grades lives in the browser, and a fifth
 * exam gets a working form with no change here.
 *
 * Kept free of React so a test can assert what a marker sees.
 */

export type ReviewForm = components["schemas"]["ReviewFormRead"];
export type ReviewField = components["schemas"]["ReviewFieldRead"];

/** One domain of the form: its rateable fields, in the rubric's order. */
export interface FormDomain {
  id: string;
  label: string;
  /** The backend refuses to complete a review that leaves this domain unrated. */
  required: boolean;
  fields: ReviewField[];
}

/** The form's fields grouped by domain, keeping the order the rubric lists them in. */
export function formDomains(form: ReviewForm | null | undefined): FormDomain[] {
  const required = new Set(form?.required_domains ?? []);
  const domains: FormDomain[] = [];
  for (const field of form?.fields ?? []) {
    let domain = domains.find((candidate) => candidate.id === field.domain_id);
    if (!domain) {
      domain = { id: field.domain_id, label: field.domain_label, required: required.has(field.domain_id), fields: [] };
      domains.push(domain);
    }
    domain.fields.push(field);
  }
  return domains;
}

export type SlotRatingSummary = components["schemas"]["SlotRagSummary"];

/** One domain of a slot's agreed ratings, named as the rubric names it. */
export interface SummaryDomain {
  id: string;
  label: string;
  value: RatingValue;
}

/**
 * The agreed rating per domain, in the order the backend sent them, each
 * named from `domain_labels` — the frozen rubric's own titles, sent with the
 * summary so no screen needs the review form (a candidate never gets one) or
 * guesses a title from an id. An id the rubric has no title for shows as the
 * id itself, which is honest about a data problem rather than hiding it.
 */
export function summaryDomains(summary: SlotRatingSummary | null | undefined): SummaryDomain[] {
  const labels = summary?.domain_labels ?? {};
  return Object.entries(summary?.by_domain ?? {}).map(([id, value]) => ({ id, label: labels[id] ?? id, value }));
}

/**
 * A saved review's ratings, keyed by path, keeping only values the rating accepts.
 *
 * `field_values` also carries notes (`tasks.comment`) and anything an older
 * form wrote; those are not ratings and are left out here.
 */
export function initialRatings(
  form: ReviewForm | null | undefined,
  fieldValues: Record<string, unknown> | null | undefined,
): Record<string, RatingValue> {
  const ratings: Record<string, RatingValue> = {};
  if (!form) return ratings;
  for (const field of form.fields ?? []) {
    const value = asRatingValue(form.rating, fieldValues?.[field.path]);
    if (value !== null) ratings[field.path] = value;
  }
  return ratings;
}

/**
 * The machine's rating at a review path, read from the marked payload.
 *
 * Review paths and payload keys are the same dotted path (`tasks.discovers_ice.score`
 * is `payload.tasks.discovers_ice.score`), which is how a marker sees what the
 * machine gave beside the rating they are about to give.
 */
export function machineRating(
  rating: Rating,
  payload: Record<string, unknown> | null | undefined,
  path: string,
): RatingValue | null {
  let cursor: unknown = payload;
  for (const segment of path.split(".")) {
    if (typeof cursor !== "object" || cursor === null || Array.isArray(cursor)) return null;
    cursor = (cursor as Record<string, unknown>)[segment];
  }
  return asRatingValue(rating, cursor);
}

/** The required domains with no rating yet, by label, so the form can say what is missing. */
export function unratedRequired(form: ReviewForm | null | undefined, ratings: Record<string, RatingValue>): string[] {
  return formDomains(form)
    .filter((domain) => domain.required && !domain.fields.some((field) => ratings[field.path] !== undefined))
    .map((domain) => domain.label);
}

/** Per-domain notes ride in `field_values` beside the ratings, as `<domain>.comment`. */
export function commentPath(domainId: string): string {
  return `${domainId}.comment`;
}

/** The notes out of a saved review's `field_values`, keyed by domain id. */
export function initialComments(
  form: ReviewForm | null | undefined,
  fieldValues: Record<string, unknown> | null | undefined,
): Record<string, string> {
  const comments: Record<string, string> = {};
  for (const domain of formDomains(form)) {
    const value = fieldValues?.[commentPath(domain.id)];
    if (typeof value === "string") comments[domain.id] = value;
  }
  return comments;
}

/** Ratings and non-empty notes, as the `field_values` a save sends. */
export function fieldValuesFor(
  ratings: Record<string, RatingValue>,
  comments: Record<string, string> = {},
): Record<string, RatingValue | string> {
  const values: Record<string, RatingValue | string> = { ...ratings };
  for (const [domainId, text] of Object.entries(comments)) {
    const trimmed = text.trim();
    if (trimmed) values[commentPath(domainId)] = trimmed;
  }
  return values;
}

/**
 * The values a rating input offers, best first.
 *
 * A scale offers its letters; met / not met offers both; a whole-number range
 * offers every value from maximum to minimum while that is a short row of
 * buttons (11 or fewer). A longer or decimal range (`step: "number"`) returns
 * null, and the input is a number field instead.
 */
export function ratingChoices(rating: Rating): RatingValue[] | null {
  if (isEnumerated(rating)) return [...(rating.scale ?? [])];
  if (rating.kind === "boolean") return [true, false];
  if (rating.step !== "integer") return null;
  const minimum = Math.ceil(rating.minimum ?? 0);
  const maximum = Math.floor(rating.maximum ?? minimum);
  const count = maximum - minimum + 1;
  if (count < 1 || count > 11) return null;
  return Array.from({ length: count }, (_, index) => maximum - index);
}

/**
 * The badge colour one rating reads as where no display tones are sent
 * (review summaries and the cohort report carry the rating, not the display).
 *
 * By position, not by letter: a scale's best value is success and its worst
 * danger, so "Excellent / Pass / Fail" colours the same way as G / A / R. A
 * range reads by its fraction of the maximum, in thirds.
 */
export function ratingVariant(
  rating: Rating | null | undefined,
  value: unknown,
): "success" | "warning" | "danger" | "neutral" {
  if (!rating) return "neutral";
  if (isEnumerated(rating)) {
    const scale = rating.scale ?? [];
    const index = typeof value === "string" ? scale.indexOf(value) : -1;
    if (index < 0) return "neutral";
    if (index === 0) return "success";
    return index === scale.length - 1 ? "danger" : "warning";
  }
  const fraction = ratingFraction(rating, value);
  if (fraction === null) return "neutral";
  if (fraction >= 2 / 3) return "success";
  return fraction >= 1 / 3 ? "warning" : "danger";
}

/**
 * What the lead is told after a save, from the status the backend stored
 * (not the button pressed), so "completed" is only claimed once it is.
 */
export function leadSaveNote(storedStatus: string): string {
  return storedStatus === "completed" ? "Review completed." : "Draft saved.";
}
