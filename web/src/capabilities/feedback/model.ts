/**
 * Turning one scored payload into something renderable, whatever framework
 * produced it.
 *
 * The old consumer client hardcoded the SCA framework's three domains and
 * eleven task names into TypeScript interfaces, then wrote a fourth copy of
 * the same model for the institution client. PLAB, CASC and Ortho render
 * through the same screens, so any exam whose framework differs either looked
 * broken or needed its own components.
 *
 * Here the payload is read structurally: a group is an object whose values
 * look like scored competencies, and narrative is whatever `actionable_feedback`
 * holds. A framework the frontend has never heard of still renders, which is
 * the property that matters — the backend owns the marking model and the
 * frontend owns none of it.
 */

export type Rag = "R" | "A" | "G";

export const RAG_LABEL: Record<Rag, string> = {
  R: "Needs work",
  A: "Developing",
  G: "Good",
};

export interface Competency {
  key: string;
  label: string;
  score: Rag | null;
  quote: string | null;
  explanation: string | null;
}

export interface CompetencyGroup {
  key: string;
  label: string;
  competencies: Competency[];
  /** The group's own summary, when the framework produced one. */
  score: Rag | null;
  strengths: string[];
  improvements: string[];
  actions: string[];
}

export interface PriorityAction {
  area: string;
  currentLevel: string | null;
  steps: string[];
  expectedOutcome: string | null;
}

/**
 * A clinical-analysis section: a paragraph, a list, or both.
 *
 * The SCA framework writes ten of these as arrays of strings (missed history,
 * key positives, safety considerations…) and one as a sentence. Reading both
 * shapes here is what lets a framework that words it differently still render.
 */
export interface AnalysisSection {
  key: string;
  label: string;
  body: string | null;
  items: string[];
}

/** One line of what the live panel showed while the consultation ran. */
export interface CoverageEntry {
  id: string;
  label: string;
  covered: boolean;
  quote: string | null;
  seq: number;
}

export interface NormalisedFeedback {
  groups: CompetencyGroup[];
  priorities: PriorityAction[];
  /** Anything the framework produced that is prose rather than scores. */
  analysis: AnalysisSection[];
  /** What was ticked off live, in the order it happened. */
  coverage: CoverageEntry[];
}

/** Domains that are narrative wrappers rather than scored competency groups. */
const NON_SCORING = new Set(["actionable_feedback", "clinical_analysis", "overall_priorities", "live_coverage"]);

function isRag(value: unknown): value is Rag {
  return value === "R" || value === "A" || value === "G";
}

function titleise(key: string): string {
  return key
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function readCompetency(key: string, value: unknown): Competency | null {
  const record = asRecord(value);
  if (!record || !("score" in record)) return null;
  return {
    key,
    label: titleise(key),
    score: isRag(record.score) ? record.score : null,
    quote: typeof record.supporting_phrase === "string" ? record.supporting_phrase : null,
    explanation: typeof record.score_explanation === "string" ? record.score_explanation : null,
  };
}

export function normaliseFeedback(payload: Record<string, unknown>): NormalisedFeedback {
  const actionable = asRecord(payload.actionable_feedback) ?? {};
  const groups: CompetencyGroup[] = [];

  for (const [key, value] of Object.entries(payload)) {
    if (NON_SCORING.has(key)) continue;
    const record = asRecord(value);
    if (!record) continue;

    const competencies = Object.entries(record)
      .map(([childKey, childValue]) => readCompetency(childKey, childValue))
      .filter((competency): competency is Competency => competency !== null);

    if (competencies.length === 0) continue;

    // `tasks` pairs with `tasks_feedback`, which is where the framework puts
    // the narrative for the same domain.
    const narrative = asRecord(actionable[`${key}_feedback`]) ?? findNarrative(actionable, key);

    groups.push({
      key,
      label: titleise(key),
      competencies,
      score: narrative && isRag(narrative.score) ? narrative.score : null,
      strengths: asStringList(narrative?.strengths),
      improvements: asStringList(narrative?.improvements),
      actions: asStringList(narrative?.suggested_actions),
    });
  }

  return {
    groups,
    priorities: readPriorities(actionable.overall_priorities ?? payload.overall_priorities),
    analysis: readAnalysis(payload.clinical_analysis),
    coverage: readCoverage(payload.live_coverage),
  };
}

/**
 * `relating_to_others` is scored but its narrative key is `relating_feedback`,
 * so an exact match misses it. Falling back to a prefix keeps the pairing
 * without hardcoding the framework's spelling.
 */
function findNarrative(
  actionable: Record<string, unknown>,
  key: string,
): Record<string, unknown> | null {
  const stem = key.split("_")[0];
  if (!stem) return null;
  for (const [candidate, value] of Object.entries(actionable)) {
    if (candidate.startsWith(stem) && candidate.endsWith("_feedback")) {
      const record = asRecord(value);
      if (record) return record;
    }
  }
  return null;
}

function readPriorities(value: unknown): PriorityAction[] {
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => {
    const record = asRecord(item);
    if (!record) return [];
    return [
      {
        area: typeof record.area === "string" ? record.area : "Priority",
        currentLevel: typeof record.current_level === "string" ? record.current_level : null,
        steps: asStringList(record.improvement_steps),
        expectedOutcome:
          typeof record.expected_outcome === "string" ? record.expected_outcome : null,
      },
    ];
  });
}

function readAnalysis(value: unknown): AnalysisSection[] {
  const record = asRecord(value);
  if (!record) return [];
  return Object.entries(record).flatMap(([key, item]) => {
    const body = typeof item === "string" && item.trim().length > 0 ? item : null;
    const items = asStringList(item).filter((entry) => entry.trim().length > 0);
    if (!body && items.length === 0) return [];
    return [{ key, label: titleise(key), body, items }];
  });
}

/**
 * The live panel's record, which is not a score.
 *
 * Coverage says what was done; the RAG grades say how well. The two can
 * legitimately disagree — covering something badly still covers it — so this
 * is normalised separately and the screen frames it as a record.
 */
function readCoverage(value: unknown): CoverageEntry[] {
  if (!Array.isArray(value)) return [];
  return value
    .flatMap((item, index) => {
      const record = asRecord(item);
      if (!record) return [];
      const label = typeof record.label === "string" ? record.label : null;
      if (!label) return [];
      return [
        {
          id: typeof record.competency_id === "string" ? record.competency_id : `${index}`,
          label,
          covered: record.state === "covered",
          quote: typeof record.quote === "string" ? record.quote : null,
          seq: typeof record.seq === "number" ? record.seq : index,
        },
      ];
    })
    .sort((a, b) => a.seq - b.seq);
}

/** How many of each grade, for a summary line. */
export function ragTally(groups: CompetencyGroup[]): Record<Rag, number> {
  const tally: Record<Rag, number> = { R: 0, A: 0, G: 0 };
  for (const group of groups) {
    for (const competency of group.competencies) {
      if (competency.score) tally[competency.score] += 1;
    }
  }
  return tally;
}
