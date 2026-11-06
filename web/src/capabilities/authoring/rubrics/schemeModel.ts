/**
 * The marking scheme as an author sees it: Domains and Competencies, one Scale,
 * a Pass rule and Feedback. Pure data and pure edits, no React.
 *
 * The union types below are literal on purpose: `api/tests/contract/test_shared_vocabulary.py`
 * reads them and compares them with the backend's constants.
 */

import { getAt, isJsonObject, parsePath, pathText, setAt, type JsonPath } from "@/capabilities/authoring/rubrics/jsonPath";

export type FeedbackKind = "strengths" | "improvements" | "actions" | "quotes" | "summary" | "flags" | "reason" | "note";
export type FeedbackShape = "line" | "paragraph" | "list";
export type ScoreKind = "labels" | "sum" | "mean" | "percent";
export type ScaleStep = "whole" | "any";
export type BlockKind = "domain" | "notes" | "custom";
export type RuleType = "score" | "labels";
export type ShowKey = "overall" | "domainScores" | "wentWell" | "workOn" | "quotes";
export interface Level { value: string | boolean; label?: string; points: number }
interface LevelScale { id: string; name: string; levels: Level[] }
interface NumberScale { id: string; name: string; from: number; to: number; step: ScaleStep }
export type Scale = LevelScale | NumberScale;
export interface Competency { id: string; label: string; instructions?: string; descriptors?: Record<string, string> }
interface FeedbackItem { id: string; kind: FeedbackKind; shape: FeedbackShape; label?: string; instructions?: string; required?: boolean; advanced?: Record<string, unknown> }
interface CustomItem { id: string | null; custom: unknown }
export type Feedback = FeedbackItem | CustomItem;
export interface Mark { field: string; label?: string; instructions?: string; [key: string]: unknown }
export interface DomainBlock { block: "domain"; id: string; title?: string; instructions?: string; scale?: string; live?: boolean; optional?: boolean; description?: string; competencies: Competency[]; feedback?: Feedback[]; competencyFeedback?: Feedback[]; mark?: Mark; advanced?: Record<string, unknown> }
export interface NotesBlock { block: "notes"; id: string; title?: string; instructions?: string; single?: boolean; feedback: Feedback[]; advanced?: Record<string, unknown> }
interface CustomBlock { block: "custom"; raw: unknown }
export type Block = DomainBlock | NotesBlock | CustomBlock;
export type Rule = { type: "score"; atLeast: number } | { type: "labels"; atLeast: number; of: "count" | "percent"; value: string | boolean | number };
export interface PassPart { score?: ScoreKind; rule?: Rule; everyDomainPasses?: boolean }
export type Tone = "supportive" | "formal" | "brief" | null;
export interface Scheme { schemaVersion: 3; instructions?: string; mark?: Mark; scales?: Scale[]; outline: Block[]; competencyFeedback?: Feedback[]; pass?: { domain?: PassPart; overall?: PassPart }; show?: Partial<Record<ShowKey, boolean>>; tone?: Tone; advanced?: Record<string, unknown>; basedOn?: unknown }
export interface Problem { path: string; message: string }

/* ------------------------------------------------------------------ words */

interface ScalePreset { id: string; label: string; scale: Scale }
export const SCALE_PRESETS: readonly [ScalePreset, ScalePreset, ScalePreset, ScalePreset] = [
  { id: "rag", label: "Red, Amber, Green", scale: { id: "rag", name: "RAG", levels: [{ value: "G", label: "Green", points: 3 }, { value: "A", label: "Amber", points: 2 }, { value: "R", label: "Red", points: 1 }] } },
  { id: "pass_fail", label: "Pass or fail", scale: { id: "pass_fail", name: "Pass / Fail", levels: [{ value: true, label: "Pass", points: 1 }, { value: false, label: "Fail", points: 0 }] } },
  { id: "marks", label: "0 to 10, whole numbers", scale: { id: "marks", name: "0 to 10", from: 0, to: 10, step: "whole" } },
  { id: "clear_pass", label: "Clear pass to clear fail", scale: { id: "clear_pass", name: "Clear pass to clear fail", levels: [{ value: "clear_pass", label: "Clear pass", points: 3 }, { value: "pass", label: "Pass", points: 2 }, { value: "fail", label: "Fail", points: 1 }, { value: "clear_fail", label: "Clear fail", points: 0 }] } },
];

export const FEEDBACK_KIND_WORDS: Record<FeedbackKind, string> = { strengths: "What went well", improvements: "What to improve", actions: "Next steps", quotes: "Quotes from the transcript", summary: "Summary", flags: "Safety concerns", reason: "Why this rating", note: "Note" };
export const FEEDBACK_SHAPE_WORDS: Record<FeedbackShape, string> = { line: "One line", paragraph: "A paragraph", list: "A list" };
export const SCORE_WORDS: Record<ScoreKind, string> = { labels: "Count of ratings", sum: "Total of points", mean: "Average", percent: "Percentage" };
export const SHOW_WORDS: Record<ShowKey, { label: string; hint: string }> = {
  overall: { label: "Overall result and band", hint: "The total, outcome and band." },
  domainScores: { label: "Score per domain", hint: "The figure each domain gets." },
  wentWell: { label: "What went well", hint: "The What went well feedback." },
  workOn: { label: "What to work on", hint: "The What to improve and Next steps feedback." },
  quotes: { label: "Transcript quotes", hint: "The Quotes from the transcript feedback." },
};
export const TONE_WORDS = [
  { value: null, label: "As written", hint: "The marking instructions decide." },
  { value: "supportive", label: "Supportive and direct", hint: "Warm, plain and specific." },
  { value: "formal", label: "Formal examiner", hint: "Impersonal, as a mark scheme." },
  { value: "brief", label: "Brief", hint: "Short sentences, no padding." },
] as const;
export const STARTING_SCALE_WORDS: Record<string, string> = { rag: "Red, Amber, Green", scale: "Named levels", range: "Numbers", boolean: "Yes or no" };

const SCORE_NOUN: Record<ScoreKind, string> = { labels: "share of top ratings", sum: "total", mean: "average", percent: "percentage" };
const SHOW_KEYS = Object.keys(SHOW_WORDS) as ShowKey[];
export { SHOW_KEYS };

/* ------------------------------------------------------------------ guards */

export const isCustom = (item: Feedback): item is CustomItem => "custom" in item;
export const isNumberScale = (scale: Scale | undefined): scale is NumberScale => scale !== undefined && "from" in scale;
export const cannotShow = (s: Scheme): boolean => s.advanced?.raw !== undefined;
export function readScheme(value: unknown): Scheme {
  // Anything else is kept whole under advanced.raw, as the api does, and shown as JSON.
  if (!isJsonObject(value) || value.schemaVersion !== 3) return { schemaVersion: 3, outline: [], advanced: { raw: value } };
  const scheme = value as unknown as Scheme;
  // A domain saved without competencies still draws.
  const outline = (Array.isArray(scheme.outline) ? scheme.outline : []).map((b) => (b.block === "domain" && !Array.isArray(b.competencies) ? { ...b, competencies: [] } : b));
  return { ...scheme, outline };
}
/** The text of the JSON editor as a scheme, or the sentence that says why it is not one. */
export function parseSchemeJson(text: string): { scheme: Scheme } | { error: string } {
  let parsed: unknown;
  try {
    parsed = JSON.parse(text);
  } catch (cause) {
    return { error: `This is not valid JSON: ${cause instanceof Error ? cause.message : String(cause)}` };
  }
  if (!isJsonObject(parsed) || parsed.schemaVersion !== 3) return { error: "The scheme must say schemaVersion 3." };
  return { scheme: readScheme(parsed) };
}
export const levelWord = (level: Level): string => level.label ?? String(level.value);

/** The scale a domain is rated on (the scheme's first when it names none). */
export function scaleOf(s: Scheme, block?: DomainBlock): Scale | undefined {
  const scales = s.scales ?? [];
  return scales.find((scale) => scale.id === block?.scale) ?? scales[0];
}

/* ------------------------------------------------------------------ blank */

/** Kept in sync with `authoring.blank_scheme()` in the api. */
export function blank(): Scheme {
  return {
    schemaVersion: 3,
    mark: { field: "score", role: "rating", label: "Rating" },
    scales: [{ id: "rag", name: "RAG", levels: [{ value: "G", label: "Green", points: 3 }, { value: "A", label: "Amber", points: 2 }, { value: "R", label: "Red", points: 1 }] }],
    outline: [{ block: "domain", id: "domain_1", title: "Domain 1", instructions: "", scale: "rag", competencies: [{ id: "competency_1", label: "Competency 1", instructions: "" }] }],
    competencyFeedback: [
      { id: "evidence", kind: "quotes", shape: "paragraph", label: "Evidence" },
      { id: "explanation", kind: "reason", shape: "paragraph", label: "Explanation" },
    ],
  };
}

/* ------------------------------------------------------------------ pass-rule sentences */

/** One sentence per pass rule, worded exactly as the marker applies it. */
export function ruleSentence(which: "domain" | "overall", part: PassPart | undefined, scale: Scale | undefined, domainHasRule = true): string {
  const rule = part?.rule;
  if (!rule) return which === "domain" ? "Domains have no pass line." : "The station has no pass line.";
  const subject = which === "domain" ? "Pass a domain when" : "Pass the station when";
  const every = which === "overall" && part?.everyDomainPasses === true && domainHasRule;
  let sentence: string;
  if (rule.type === "score") {
    const kind = part?.score;
    sentence = `${subject} its ${kind ? SCORE_NOUN[kind] : "score"} is at least ${rule.atLeast}${kind === "percent" ? "%" : ""}`;
  } else {
    const level = isNumberScale(scale) ? undefined : scale?.levels.find((l) => l.value === rule.value);
    const word = level ? levelWord(level) : rule.value === undefined ? "at the level you pick" : String(rule.value);
    const rated = isNumberScale(scale) ? `rated ${word} or more` : `rated ${word} or better`;
    const amount = rule.of === "percent" ? `${rule.atLeast}%` : String(rule.atLeast);
    sentence = `${subject} at least ${amount} of ${which === "domain" ? "its" : "all"} competencies are ${rated}`;
  }
  return every ? `${sentence}, and every domain passes.` : `${sentence}.`;
}

/* ------------------------------------------------------------------ pure edits */

const blockId = (b: Block): string => ("id" in b ? b.id : "");

/** `${prefix}_${n}` with the smallest n not in `used`. */
function nextId(prefix: string, used: Iterable<string>): string {
  const taken = new Set(used);
  let n = 1;
  while (taken.has(`${prefix}_${n}`)) n += 1;
  return `${prefix}_${n}`;
}

function nextNumber(prefix: string, used: Iterable<string>): number {
  return Number(nextId(prefix, used).slice(prefix.length + 1));
}

const replaceAt = <T,>(list: readonly T[], index: number, next: T): T[] => list.map((item, i) => (i === index ? next : item));
function reorder<T>(list: readonly T[], from: number, to: number): T[] {
  if (from === to || from < 0 || to < 0 || from >= list.length || to >= list.length) return [...list];
  const copy = [...list];
  const [moved] = copy.splice(from, 1);
  copy.splice(to, 0, moved as T);
  return copy;
}

const firstScaleId = (s: Scheme): string | undefined => s.scales?.[0]?.id;
const withOutline = (s: Scheme, outline: Block[]): Scheme => ({ ...s, outline });
const domainAt = (s: Scheme, i: number): DomainBlock | undefined => {
  const b = s.outline[i];
  return b?.block === "domain" ? b : undefined;
};

export function addDomain(s: Scheme): Scheme {
  const n = nextNumber("domain", s.outline.map(blockId));
  const block: DomainBlock = { block: "domain", id: `domain_${n}`, title: `Domain ${n}`, instructions: "", scale: firstScaleId(s), competencies: [{ id: "competency_1", label: "Competency 1", instructions: "" }] };
  return withOutline(s, [...s.outline, block]);
}

export function addCompetency(s: Scheme, blockIndex: number): Scheme {
  const domain = domainAt(s, blockIndex);
  if (!domain) return s;
  const n = nextNumber("competency", domain.competencies.map((c) => c.id));
  return updateBlock(s, blockIndex, { competencies: [...domain.competencies, { id: `competency_${n}`, label: `Competency ${n}`, instructions: "" }] });
}

export function addNotes(s: Scheme): Scheme {
  const n = nextNumber("notes", s.outline.map(blockId));
  return withOutline(s, [...s.outline, { block: "notes", id: `notes_${n}`, title: `Notes ${n}`, feedback: [] }]);
}

export type FeedbackWhere = { level: "competency" } | { level: "domain"; blockIndex: number } | { level: "notes"; blockIndex: number };

function feedbackList(s: Scheme, where: FeedbackWhere): Feedback[] {
  if (where.level === "competency") return s.competencyFeedback ?? [];
  const b = s.outline[where.blockIndex];
  return b && b.block !== "custom" ? (b.feedback ?? []) : [];
}
function setFeedbackList(s: Scheme, where: FeedbackWhere, list: Feedback[]): Scheme {
  if (where.level === "competency") return { ...s, competencyFeedback: list };
  return updateBlock(s, where.blockIndex, { feedback: list });
}
function allFeedbackIds(s: Scheme): string[] {
  const own = (list?: Feedback[]) => (list ?? []).flatMap((f) => (f.id ? [f.id] : []));
  return [...own(s.competencyFeedback), ...s.outline.flatMap((b) => (b.block === "custom" ? [] : own(b.feedback)))];
}

export function addFeedback(s: Scheme, where: FeedbackWhere): Scheme {
  const n = nextNumber("feedback", allFeedbackIds(s));
  return setFeedbackList(s, where, [...feedbackList(s, where), { id: `feedback_${n}`, kind: "note", shape: "paragraph", label: `Feedback ${n}` }]);
}
export function updateFeedback(s: Scheme, where: FeedbackWhere, k: number, patch: Partial<FeedbackItem>): Scheme {
  const list = feedbackList(s, where);
  const item = list[k];
  if (!item || isCustom(item)) return s;
  return setFeedbackList(s, where, replaceAt(list, k, { ...item, ...patch }));
}
export function removeFeedback(s: Scheme, where: FeedbackWhere, k: number): Scheme {
  return setFeedbackList(s, where, feedbackList(s, where).filter((_, i) => i !== k));
}

export function updateBlock(s: Scheme, i: number, patch: Partial<DomainBlock> | Partial<NotesBlock>): Scheme {
  const b = s.outline[i];
  if (!b || b.block === "custom") return s;
  return withOutline(s, replaceAt<Block>(s.outline, i, { ...b, ...patch } as Block));
}
export function updateCompetency(s: Scheme, i: number, j: number, patch: Partial<Competency>): Scheme {
  const domain = domainAt(s, i);
  const competency = domain?.competencies[j];
  if (!domain || !competency) return s;
  return updateBlock(s, i, { competencies: replaceAt(domain.competencies, j, { ...competency, ...patch }) });
}
export function updateScale(s: Scheme, scale: Scale): Scheme {
  return { ...s, scales: [scale, ...(s.scales ?? []).slice(1)] };
}
export function updatePass(s: Scheme, which: "domain" | "overall", part: PassPart | undefined): Scheme {
  const pass = { ...(s.pass ?? {}) };
  if (part === undefined) delete pass[which];
  else pass[which] = part;
  // "Every domain passes" means nothing once domains have no pass line.
  if (which === "domain" && part?.rule === undefined && pass.overall?.everyDomainPasses !== undefined) {
    const { everyDomainPasses: _every, ...overall } = pass.overall;
    pass.overall = overall;
  }
  return { ...s, pass };
}
export const setShow = (s: Scheme, key: ShowKey, on: boolean): Scheme => ({ ...s, show: { ...(s.show ?? {}), [key]: on } });
export const setTone = (s: Scheme, tone: Tone): Scheme => ({ ...s, tone });

export function removeBlock(s: Scheme, i: number): Scheme {
  return withOutline(s, s.outline.filter((_, at) => at !== i));
}
/** A domain keeps at least one competency: removing the last returns `s` unchanged. */
export function removeCompetency(s: Scheme, i: number, j: number): Scheme {
  const domain = domainAt(s, i);
  if (!domain || domain.competencies.length <= 1) return s;
  return updateBlock(s, i, { competencies: domain.competencies.filter((_, at) => at !== j) });
}
export const moveBlock = (s: Scheme, from: number, to: number): Scheme => withOutline(s, reorder(s.outline, from, to));
export function moveCompetency(s: Scheme, i: number, from: number, to: number): Scheme {
  const domain = domainAt(s, i);
  return domain ? updateBlock(s, i, { competencies: reorder(domain.competencies, from, to) }) : s;
}
/** A copy right after the original, with its own id; competencies keep theirs (ids are per domain). */
export function duplicateBlock(s: Scheme, i: number): Scheme {
  const b = s.outline[i];
  if (!b || b.block === "custom") return s;
  const prefix = b.block === "domain" ? "domain" : "notes";
  const id = nextId(prefix, s.outline.map(blockId));
  const copy: Block = { ...structuredClone(b), id, title: `${b.title ?? ""} copy`.trim() };
  // A single notes block is one field named by its feedback item: the copy needs its own.
  if (copy.block === "notes" && copy.single && copy.feedback[0] && !isCustom(copy.feedback[0])) {
    const ids = s.outline.flatMap((o) => (o.block === "notes" && o.single ? o.feedback.map((f) => f.id ?? "") : []));
    copy.feedback[0] = { ...copy.feedback[0], id: nextId(copy.feedback[0].id.replace(/_\d+$/, "") || "note", ids) };
  }
  return withOutline(s, [...s.outline.slice(0, i + 1), copy, ...s.outline.slice(i + 1)]);
}
export function duplicateCompetency(s: Scheme, i: number, j: number): Scheme {
  const domain = domainAt(s, i);
  const source = domain?.competencies[j];
  if (!domain || !source) return s;
  const id = nextId("competency", domain.competencies.map((c) => c.id));
  const copy: Competency = { ...structuredClone(source), id, label: `${source.label} copy` };
  return updateBlock(s, i, { competencies: [...domain.competencies.slice(0, j + 1), copy, ...domain.competencies.slice(j + 1)] });
}

/**
 * Switch to a preset scale: every domain uses it, what earns each level is cleared (the levels are
 * different), and a pass rule naming a level the new scale lacks loses that level.
 */
export function applyPreset(s: Scheme, presetId: string): Scheme {
  const preset = SCALE_PRESETS.find((p) => p.id === presetId);
  if (!preset) return s;
  const scale = structuredClone(preset.scale);
  const has = (value: unknown) => !isNumberScale(scale) && scale.levels.some((l) => l.value === value);
  const before = s.scales?.[0];
  const pointsBefore = (value: unknown) => (before && !isNumberScale(before) ? before.levels.find((l) => l.value === value)?.points : undefined);
  /** The level of the new scale worth the nearest points to the one the rule named; the better level wins a tie. */
  const nearest = (value: unknown): Level | undefined => {
    const was = pointsBefore(value);
    if (was === undefined || isNumberScale(scale)) return undefined;
    return [...scale.levels].sort((a, b) => Math.abs(a.points - was) - Math.abs(b.points - was) || b.points - a.points)[0];
  };
  /** The number a level is worth on a number scale: its share of the old scale's points, spread over the range. */
  const numberFor = (value: unknown): number => {
    const was = pointsBefore(value);
    if (!isNumberScale(scale) || was === undefined || !before || isNumberScale(before)) return isNumberScale(scale) ? scale.to : 0;
    const points = before.levels.map((l) => l.points);
    const low = Math.min(...points);
    const high = Math.max(...points);
    return high === low ? scale.to : Math.round(scale.from + ((was - low) / (high - low)) * (scale.to - scale.from));
  };
  const fix = (part: PassPart | undefined): PassPart | undefined => {
    if (part?.rule?.type !== "labels") return part;
    if (isNumberScale(scale)) return typeof part.rule.value === "number" && before && isNumberScale(before) ? part : { ...part, rule: { ...part.rule, value: numberFor(part.rule.value) } };
    if (has(part.rule.value)) return part;
    const near = nearest(part.rule.value);
    if (near) return { ...part, rule: { ...part.rule, value: near.value } };
    const { value: _dropped, ...rest } = part.rule;
    return { ...part, rule: rest as unknown as Rule };
  };
  const outline = s.outline.map((b): Block =>
    b.block === "domain" ? { ...b, scale: scale.id, competencies: b.competencies.map(({ descriptors: _d, ...c }) => c) } : b,
  );
  const pass = s.pass ? { ...s.pass, domain: fix(s.pass.domain), overall: fix(s.pass.overall) } : s.pass;
  // Tones are score thresholds written against the old scale; on the new one they no longer fit and block publishing.
  const { tones: _tones, ...advanced } = s.advanced ?? {};
  return { ...s, scales: [scale], outline, pass, advanced: s.advanced ? advanced : s.advanced };
}

/** True when switching scale drops the colour tones the scheme carries, so the author is told first. */
export function presetClearsTones(s: Scheme): boolean {
  return s.advanced?.tones !== undefined;
}

/** True when switching to this preset changes a pass rule that counts ratings, so the author is told first. */
export function presetMovesRules(s: Scheme, presetId: string): boolean {
  return JSON.stringify(applyPreset(s, presetId).pass ?? null) !== JSON.stringify(s.pass ?? null);
}

/** What happened to the outline, for keeping the picked row on the row it was. */
export type OutlineChange =
  | { kind: "move"; from: number; to: number }
  | { kind: "insert"; at: number }
  | { kind: "remove"; at: number }
  | { kind: "moveCompetency"; block: number; from: number; to: number }
  | { kind: "insertCompetency"; block: number; at: number }
  | { kind: "removeCompetency"; block: number; at: number };
export interface OutlineFocus { block: number; competency?: number }

const shift = (n: number, from: number, to: number): number => (n === from ? to : from < to && n > from && n <= to ? n - 1 : to < from && n >= to && n < from ? n + 1 : n);

/** The picked row after an edit moved things: it follows its row, and is dropped when that row is gone. */
export function remapFocus(focus: OutlineFocus | null, change: OutlineChange): OutlineFocus | null {
  if (focus === null) return null;
  const { block, competency } = focus;
  const keep = (b: number, c = competency): OutlineFocus => (c === undefined ? { block: b } : { block: b, competency: c });
  switch (change.kind) {
    case "move": return keep(shift(block, change.from, change.to));
    case "insert": return keep(block >= change.at ? block + 1 : block);
    case "remove": return block === change.at ? null : keep(block > change.at ? block - 1 : block);
    default:
      if (block !== change.block || competency === undefined) return focus;
      if (change.kind === "moveCompetency") return keep(block, shift(competency, change.from, change.to));
      if (change.kind === "insertCompetency") return keep(block, competency >= change.at ? competency + 1 : competency);
      return competency === change.at ? null : keep(block, competency > change.at ? competency - 1 : competency);
  }
}

/* ------------------------------------------------------------------ paths and problems */


/** The messages about exactly this path. */
export function problemsAt(problems: readonly Problem[], path: JsonPath): string[] {
  const target = pathText(path);
  return problems.filter((p) => p.path === target).map((p) => p.message);
}

/** How many problems are at this path or anywhere inside it. */
export function problemsWithin(problems: readonly Problem[], path: JsonPath): number {
  const target = pathText(path);
  if (target === "") return problems.length;
  return problems.filter((p) => p.path === target || p.path.startsWith(`${target}.`) || p.path.startsWith(`${target}[`)).length;
}

/** The problems a publish refusal carried (`invalid_rubric`, `details.errors`). */
export function problemsFromDetails(details: Record<string, unknown> | null): Problem[] {
  const errors = details?.errors;
  if (!Array.isArray(errors)) return [];
  return errors.flatMap((item) => (isJsonObject(item) && typeof item.path === "string" && typeof item.message === "string" ? [{ path: item.path, message: item.message }] : []));
}

/** Where a problem is, in words an author recognises. */
export function placeLabel(s: Scheme, path: string): string {
  if (path === "") return "The whole scheme";
  const segments = parsePath(path);
  const [head, index, tail, second] = segments;
  if (head === "outline" && typeof index === "number") {
    const b = s.outline[index];
    const name = b && b.block !== "custom" ? ((b.title ?? "").trim() || b.id) : "Custom block";
    if (tail === "competencies" && typeof second === "number" && b?.block === "domain") {
      const c = b.competencies[second];
      return `${name}, ${(c?.label ?? "").trim() || c?.id || `Competency ${second + 1}`}`;
    }
    return name;
  }
  if (head === "scales") return "Scale";
  if (head === "pass") return index === "overall" ? "Pass rule, station" : index === "domain" ? "Pass rule, domains" : "Pass rule";
  if (head === "competencyFeedback") return "Feedback, every competency";
  if (head === "show" || head === "tone") return "What the candidate sees";
  if (head === "advanced") return "Advanced";
  return "Advanced";
}

/** The builder tab a problem belongs to (a red count on the tab). */
export type SchemeTabId = "domains" | "scale" | "pass" | "feedback" | "advanced" | "trial" | "versions";
export function tabOfPath(path: string): SchemeTabId {
  const head = parsePath(path)[0];
  if (head === "outline") return "domains";
  if (head === "scales") return "scale";
  if (head === "pass") return "pass";
  if (head === "competencyFeedback" || head === "show" || head === "tone") return "feedback";
  return "advanced";
}

/* ------------------------------------------------------------------ drafted instructions */

interface Suggestion { key: string; text: string; has_instructions: boolean }

/**
 * Suggested wording written into every empty `instructions`, by the backend's key:
 * `domain`, `domain.competency`, `domain.*.field` (the mark, or a feedback item), or a lone field.
 */
export function applySuggestions(s: Scheme, items: readonly Suggestion[]): { scheme: Scheme; filled: number } {
  let next = s;
  let filled = 0;
  const seen = new Set<string>();
  for (const item of items) {
    if (item.has_instructions || item.text.trim() === "") continue;
    const path = targetPath(next, item.key);
    if (!path) continue;
    const at = pathText(path);
    if (seen.has(at)) continue;
    const target = getAt(next, path) as { instructions?: string } | undefined;
    if (!target || (typeof target.instructions === "string" && target.instructions.trim() !== "")) continue;
    seen.add(at);
    next = setAt(next, [...path, "instructions"], item.text);
    filled += 1;
  }
  return { scheme: next, filled };
}

function targetPath(s: Scheme, key: string): JsonPath | null {
  const parts = key.split(".");
  const blockAt = (id: string) => s.outline.findIndex((b) => b.block !== "custom" && b.id === id);
  const feedbackIndex = (list: Feedback[] | undefined, id: string) => (list ?? []).findIndex((f) => f.id === id);
  if (parts.length === 1) {
    const i = blockAt(parts[0] as string);
    if (i >= 0) return ["outline", i];
    const lone = s.outline.findIndex((b) => b.block === "notes" && b.single === true && b.feedback[0]?.id === parts[0]);
    return lone >= 0 ? ["outline", lone, "feedback", 0] : null;
  }
  const i = blockAt(parts[0] as string);
  const b = s.outline[i];
  if (!b || b.block === "custom") return null;
  if (parts.length === 2) {
    if (b.block === "domain") {
      const j = b.competencies.findIndex((c) => c.id === parts[1]);
      if (j >= 0) return ["outline", i, "competencies", j];
    }
    const k = feedbackIndex(b.feedback, parts[1] as string);
    return k >= 0 ? ["outline", i, "feedback", k] : null;
  }
  if (parts.length === 3 && parts[1] === "*" && b.block === "domain") {
    const field = parts[2] as string;
    if (field === b.mark?.field) return ["outline", i, "mark"];
    if (field === s.mark?.field && !b.mark) return ["mark"];
    const own = feedbackIndex(b.competencyFeedback, field);
    if (own >= 0) return ["outline", i, "competencyFeedback", own];
    const top = feedbackIndex(s.competencyFeedback, field);
    return top >= 0 ? ["competencyFeedback", top] : null;
  }
  return null;
}


/** A new level on the scale, with a value no level has. */
export function addLevel(s: Scheme): Scheme {
  const scale = scaleOf(s);
  if (!scale || isNumberScale(scale)) return s;
  const n = nextNumber("level", scale.levels.map((l) => String(l.value)));
  return updateScale(s, { ...scale, levels: [...scale.levels, { value: `level_${n}`, label: `Level ${scale.levels.length + 1}`, points: 0 }] });
}

/** Take a level off the scale, and with it what earned it and any pass rule that named it. */
export function removeLevel(s: Scheme, j: number): Scheme {
  const scale = scaleOf(s);
  const gone = scale && !isNumberScale(scale) ? scale.levels[j] : undefined;
  if (!scale || isNumberScale(scale) || !gone) return s;
  const key = String(gone.value);
  const dropRule = (part: PassPart | undefined): PassPart | undefined => {
    if (!part?.rule || part.rule.type !== "labels" || String(part.rule.value) !== key) return part;
    const { rule: _rule, ...rest } = part;
    return rest;
  };
  const outline = s.outline.map((b) =>
    b.block === "domain"
      ? { ...b, competencies: b.competencies.map((c) => { if (!c.descriptors || !(key in c.descriptors)) return c; const { [key]: _d, ...rest } = c.descriptors; return { ...c, descriptors: rest }; }) }
      : b,
  );
  const next = updateScale({ ...s, outline }, { ...scale, levels: scale.levels.filter((_, i) => i !== j) });
  return next.pass ? { ...next, pass: { domain: dropRule(next.pass.domain), overall: dropRule(next.pass.overall) } } : next;
}
