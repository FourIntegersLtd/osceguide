import type { components } from "@/foundation/platform-client";

/**
 * A marking rubric, as the screens read it.
 *
 * An exam is data, not code: the rubric says which domains a result has,
 * which fields each competency answers and what role each field plays, and
 * its display says how a mark is summed, where the pass lines are and what
 * the charts are called. Nothing in platform-web branches on an exam code
 * (sca, plab, casc, ortho) to decide any of that. A fifth exam authored on
 * the backend renders with no change here.
 *
 * The backend computes every total and every pass (`ResultTotalsRead`,
 * `Performance`). What lives here is presentation only: the tone a single
 * rating is drawn in, how a number is written, which band a total falls in.
 * These mirror `rubrics/service_scoring.py` so the colour on a chip agrees
 * with the colour the backend used when it counted a concern.
 */

export type Rating = components["schemas"]["RatingRead"];
export type MarkingRubric = components["schemas"]["MarkingRubricRead"];
export type MarkedResult = components["schemas"]["MarkedResultRead"];
export type ResultTotals = components["schemas"]["ResultTotalsRead"];
export type DomainTotal = components["schemas"]["DomainTotalRead"];

/** One rating as a marker gives it: a scale letter, a number, or met / not met. */
export type RatingValue = boolean | number | string;

/** How a set of ratings is summed (plan section 4.2). */
export type Aggregate = "ragCounts" | "ragShare" | "percentAchieved" | "sum" | "mean";

/** A colour band a fraction of the maximum falls in; `value` pins it to one scale letter. */
export interface ToneRule {
  atLeast: number;
  tone: string;
  value?: RatingValue;
}

/** A named range of station totals, e.g. Ortho's 35 to 42 is "good". */
export interface Band {
  from: number;
  to: number;
  label: string;
  tone: string;
}

/** The backend's resolved display: every default already filled in. */
export interface Display {
  domain: { aggregate: Aggregate; max: number | null; passAtLeast: number | null };
  total: {
    aggregate: Aggregate;
    max: number | null;
    passAtLeast: number | null;
    requireEveryDomain: boolean;
  };
  tones: ToneRule[];
  bands: Band[];
  labels: Record<string, string>;
  /** Which feedback fields the candidate sees (`overall`, `areaScores`, `wentWell`, `workOn`, `quotes`); absent means shown. */
  show: Record<string, boolean>;
  /** The wording tone the marker was asked for, or null when the instructions are used as written. */
  feedbackTone: string | null;
}

/* ---------- reading the untyped JSON the API sends ---------- */

type JsonObject = Record<string, unknown>;

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

const AGGREGATES: readonly Aggregate[] = ["ragCounts", "ragShare", "percentAchieved", "sum", "mean"];

function aggregateOf(value: unknown, fallback: Aggregate): Aggregate {
  return AGGREGATES.find((aggregate) => aggregate === value) ?? fallback;
}

/**
 * The display block of a rubric or a performance read.
 *
 * `display` is typed as a free-form object on the API because authors can add
 * labels; this narrows it once so every screen reads the same shape. Null when
 * there is no rubric to read (an attempt marked before rubrics existed).
 */
export function readDisplay(raw: JsonObject | null | undefined): Display | null {
  if (!isObject(raw)) return null;
  const domain = isObject(raw.domain) ? raw.domain : {};
  const total = isObject(raw.total) ? raw.total : {};
  const tones = Array.isArray(raw.tones) ? raw.tones.filter(isObject) : [];
  const bands = Array.isArray(raw.bands) ? raw.bands.filter(isObject) : [];
  const labels = isObject(raw.labels) ? raw.labels : {};
  return {
    domain: {
      aggregate: aggregateOf(domain.aggregate, "sum"),
      max: numberOrNull(domain.max),
      passAtLeast: numberOrNull(domain.passAtLeast),
    },
    total: {
      aggregate: aggregateOf(total.aggregate, "sum"),
      max: numberOrNull(total.max),
      passAtLeast: numberOrNull(total.passAtLeast),
      requireEveryDomain: total.requireEveryDomain === true,
    },
    tones: tones.map((tone) => {
      const rule: ToneRule = { atLeast: numberOrNull(tone.atLeast) ?? 0, tone: text(tone.tone) };
      const pinned = tone.value;
      if (typeof pinned === "string" || typeof pinned === "number" || typeof pinned === "boolean") {
        rule.value = pinned;
      }
      return rule;
    }),
    bands: bands.map((band) => ({
      from: numberOrNull(band.from) ?? 0,
      to: numberOrNull(band.to) ?? 0,
      label: text(band.label),
      tone: text(band.tone),
    })),
    labels: Object.fromEntries(
      Object.entries(labels).filter((entry): entry is [string, string] => typeof entry[1] === "string"),
    ),
    show: Object.fromEntries(
      Object.entries(isObject(raw.show) ? raw.show : {}).filter((entry): entry is [string, boolean] => typeof entry[1] === "boolean"),
    ),
    feedbackTone: typeof raw.feedbackTone === "string" ? raw.feedbackTone : null,
  };
}

/* ---------- one rating ---------- */

/** The scale kinds whose values are letters in a fixed order, best first. */
export function isEnumerated(rating: Rating): boolean {
  return rating.kind === "rag" || rating.kind === "scale";
}

/** A value the rating accepts, or null. `" g "` is not accepted here; the API has already normalised. */
export function asRatingValue(rating: Rating, value: unknown): RatingValue | null {
  if (isEnumerated(rating)) {
    return typeof value === "string" && (rating.scale ?? []).includes(value) ? value : null;
  }
  if (rating.kind === "boolean") return typeof value === "boolean" ? value : null;
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

/**
 * A rating as a fraction of the best one, 0 to 1.
 *
 * Mirrors `service_scoring.rating_fraction`: a scale value by its position in
 * whole percent (with G, A, R that is 1, 0.66, 0.33), a range as value over
 * maximum, a boolean as 1 or 0.
 */
export function ratingFraction(rating: Rating, value: unknown): number | null {
  const valid = asRatingValue(rating, value);
  if (valid === null) return null;
  if (isEnumerated(rating)) {
    const scale = rating.scale ?? [];
    const positionFromWorst = scale.length - scale.indexOf(String(valid));
    return Math.floor((100 * positionFromWorst) / scale.length) / 100;
  }
  if (rating.kind === "boolean") return valid ? 1 : 0;
  const maximum = rating.maximum || 1;
  return Number(valid) / maximum;
}

// The backend's `_PASS_TOLERANCE`: a fraction a hair under a line is on it.
const TOLERANCE = 1e-9;

/** The tone a fraction of the maximum falls in, highest `atLeast` first. */
export function toneForFraction(display: Display | null, fraction: number | null): string | null {
  if (!display || fraction === null) return null;
  const ordered = display.tones
    .filter((tone) => tone.value === undefined)
    .sort((left, right) => right.atLeast - left.atLeast);
  return ordered.find((tone) => fraction + TOLERANCE >= tone.atLeast)?.tone ?? null;
}

/** The tone one rating is drawn in: a tone pinned to its value, else by its fraction. */
export function ratingTone(rating: Rating, display: Display | null, value: unknown): string | null {
  const fraction = ratingFraction(rating, value);
  if (fraction === null || !display) return null;
  const pinned = display.tones.find((tone) => tone.value !== undefined && tone.value === value);
  if (pinned) return pinned.tone;
  return toneForFraction(display, fraction);
}

/** How one rating is written: `G`, `7/10`, `Met`. */
const RAG_WORDS: Record<string, string> = { G: "Green", A: "Amber", R: "Red" };

export function ratingLabel(rating: Rating | null | undefined, value: unknown): string {
  if (value === null || value === undefined || value === "") return "Not rated";
  if (!rating) return String(value);
  // The boards write a rag mark as its colour ("Green", "Amber", "Red"); an author's own scale keeps its own words.
  const word = rating.kind === "rag" && typeof value === "string" ? RAG_WORDS[value] : undefined;
  if (word) return word;
  if (rating.kind === "boolean") return value === true ? "Met" : value === false ? "Not met" : String(value);
  if (rating.kind === "range" && typeof value === "number") {
    return rating.maximum ? `${formatNumber(value)}/${formatNumber(rating.maximum)}` : formatNumber(value);
  }
  return String(value);
}

/* ---------- numbers and totals ---------- */

/** At most two decimals, trailing zeros dropped: 0.6000000001 is "0.6", 7 is "7". */
export function formatNumber(value: number): string {
  return String(Math.round(value * 100) / 100);
}

/**
 * A domain value or station total, written in its aggregate's units.
 *
 * `sum` and `mean` are in the rating's own units and read "x/max"; the three
 * share aggregates are already out of 100.
 */
export function formatAggregate(aggregate: Aggregate, value: number | null, max: number | null): string {
  if (value === null) return "Not scored";
  if (aggregate === "sum" || aggregate === "mean") {
    return max === null ? formatNumber(value) : `${formatNumber(value)}/${formatNumber(max)}`;
  }
  return `${Math.round(value)}%`;
}

/** The named band a station total falls in, if the display has bands. */
export function bandFor(display: Display | null, total: number | null): Band | null {
  if (!display || total === null) return null;
  return display.bands.find((band) => total + TOLERANCE >= band.from && total <= band.to + TOLERANCE) ?? null;
}

/** A band's own label, or its tone written as a word when the author left the label empty. */
export function bandName(band: Band): string {
  return band.label || toneWord(band.tone);
}

/** Every band as "from–to Name", for a legend: Ortho reads "0–17 Poor", "18–34 Fair", ... */
export function bandLegend(display: Display | null): string[] {
  return (display?.bands ?? []).map((band) => `${formatNumber(band.from)}–${formatNumber(band.to)} ${bandName(band)}`);
}

/** "good" to "Good". */
export function toneWord(tone: string): string {
  return tone ? tone.charAt(0).toUpperCase() + tone.slice(1) : "";
}

/**
 * The badge colour a tone reads as.
 *
 * Tones are the author's words (excellent, good, fair, weak, poor); the design
 * system has four badge colours. Anything unrecognised is neutral rather than
 * guessed.
 */
export function toneVariant(tone: string | null | undefined): "success" | "warning" | "danger" | "neutral" {
  if (tone === "excellent" || tone === "good") return "success";
  if (tone === "fair") return "warning";
  if (tone === "weak" || tone === "poor") return "danger";
  return "neutral";
}

/** "Passed", "Not passed", or nothing when the rubric sets no pass line. */
export function passWord(passed: boolean | null | undefined): string | null {
  if (passed === true) return "Passed";
  if (passed === false) return "Not passed";
  return null;
}
