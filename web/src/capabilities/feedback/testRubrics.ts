import type { MarkedResult, MarkingRubric, Rating, ResultTotals } from "@/capabilities/feedback/rubric";

/**
 * Small rubrics for tests, one per exam plus an invented fifth.
 *
 * Each is cut down from what the local platform-api serves after
 * `seed_platform.py --republish` (a competency or two per domain), with the
 * display block copied exactly, so a test reads like the screen a person
 * sees. The ward round is the backend's own "new exam is data only" fixture
 * (`tests/rubrics/test_new_exam_is_data_only.py`): no platform-web code knows
 * it exists, which is the point.
 */

type Json = Record<string, unknown>;

function rubric(rating: Rating, sections: Json[], display: Json): MarkingRubric {
  return { version_id: null, rating, structure: { sections }, display };
}

function result(payload: Json, totals: ResultTotals): MarkedResult {
  return {
    framework_id: "test",
    model_used: null,
    payload,
    policy_version: "test",
    scored_at: "2026-09-30T11:38:33Z",
    totals,
  };
}

const field = (id: string, type: string, role: string, label?: string, fields?: Json[]): Json => ({
  id,
  type,
  role,
  ...(label ? { label } : {}),
  ...(fields ? { fields } : {}),
});

/* ---------- SCA: a G / A / R scale, counted, with no pass line ---------- */

export const SCA_DISPLAY: Json = {
  bands: [],
  tones: [
    { tone: "good", value: "G", atLeast: 1.0 },
    { tone: "fair", value: "A", atLeast: 0.5 },
    { tone: "poor", value: "R", atLeast: 0.0 },
  ],
  total: { max: null, aggregate: "ragShare", passAtLeast: null, requireEveryDomain: false },
  domain: { max: null, aggregate: "ragCounts", passAtLeast: null },
  labels: {
    title: "Where you stand",
    trendSubtitle: "How your skills moved across recent sessions",
    domainSubtitle: "RAG mix by clinical domain",
  },
};

export const SCA_RATING: Rating = { kind: "rag", field: "score", scale: ["G", "A", "R"], step: "number" };

export const SCA = {
  rubric: rubric(
    SCA_RATING,
    [
      {
        id: "global_skills",
        kind: "domain",
        title: "Global skills",
        fields: [],
        competencies: [
          {
            id: "structures_consultation",
            label: "Structures consultation",
            descriptors: { G: "Clear opening, systematic history, structured closing.", A: "Misses one element.", R: "No framework." },
          },
        ],
        competencyFields: [
          field("score", "rating", "rating"),
          field("supporting_phrase", "shortText", "evidence", "Supporting phrase"),
          field("score_explanation", "longText", "explanation", "Why"),
        ],
      },
      {
        id: "clinical_analysis",
        kind: "section",
        title: "Clinical analysis",
        fields: [
          field("key_positives", "list", "strength", "Key positives"),
          field("safety_considerations", "list", "flag", "Safety considerations"),
        ],
      },
      {
        id: "actionable_feedback",
        kind: "section",
        title: "Actionable feedback",
        fields: [
          field("tasks_feedback", "group", "other", "Tasks feedback", [
            field("score", "shortText", "other", "Score"),
            field("strengths", "list", "strength", "Strengths"),
          ]),
          field("overall_priorities", "records", "action", "Overall priorities", [
            field("area", "shortText", "other", "Area"),
            field("improvement_steps", "list", "action", "Improvement steps"),
          ]),
        ],
      },
    ],
    SCA_DISPLAY,
  ),
  result: result(
    {
      global_skills: {
        structures_consultation: {
          score: "A",
          supporting_phrase: "Shall we start with what brought you in?",
          score_explanation: "Opened well but did not close.",
        },
      },
      clinical_analysis: { key_positives: ["Exertional pattern elicited"], safety_considerations: ["No red flags asked"] },
      actionable_feedback: {
        tasks_feedback: { score: "A", strengths: ["Open question first"] },
        overall_priorities: [{ area: "Red flags", improvement_steps: ["Ask about radiation"] }, { area: "", improvement_steps: [] }],
      },
    },
    {
      total: 10.344827586206897,
      max: null,
      fraction: 0.10344827586206896,
      passed: null,
      critical_count: 17,
      domains: [{ id: "global_skills", label: "Global skills", value: 28.571428571428573, counts: { G: 2, A: 3, R: 2 }, passed: null }],
    },
  ),
};

/* ---------- PLAB: a 0..1 range, summed per domain, every domain must pass ---------- */

export const PLAB_DISPLAY: Json = {
  bands: [],
  tones: [
    { tone: "good", atLeast: 0.8 },
    { tone: "fair", atLeast: 0.6 },
    { tone: "poor", atLeast: 0 },
  ],
  total: { max: 12.0, aggregate: "sum", passAtLeast: 7, requireEveryDomain: true },
  domain: { max: 4.0, aggregate: "sum", passAtLeast: 2 },
  labels: {
    passLabel: "Pass (7/12)",
    trendSubtitle: "Station score over time",
    domainSubtitle: "Average score out of 4",
    domainPassLabel: "Min threshold",
  },
};

export const PLAB = {
  rubric: rubric(
    { kind: "range", field: "score", scale: [], minimum: 0, maximum: 1, step: "number" },
    [
      {
        id: "data_gathering",
        kind: "domain",
        title: "Data gathering",
        fields: [],
        competencies: [{ id: "examination", label: "Examination", descriptors: {} }],
        competencyFields: [
          field("score", "rating", "rating"),
          field("completed", "list", "strength", "Completed"),
          field("critical_flags", "list", "flag", "Critical flags"),
          field("missed", "list", "improvement", "Missed"),
        ],
      },
    ],
    PLAB_DISPLAY,
  ),
  result: result(
    {
      data_gathering: {
        examination: {
          score: 0,
          completed: [],
          critical_flags: ["No observations for chest pain"],
          missed: ["No cardiovascular examination"],
        },
      },
    },
    {
      total: 4.6,
      max: 12,
      fraction: 0.3833333333333333,
      passed: false,
      critical_count: 15,
      domains: [{ id: "data_gathering", label: "Data gathering", value: 1.2, counts: {}, passed: false }],
    },
  ),
};

/* ---------- CASC: met / not met, as a percentage, pass at 80 ---------- */

export const CASC_DISPLAY: Json = {
  bands: [],
  tones: [
    { tone: "good", atLeast: 0.8 },
    { tone: "poor", atLeast: 0 },
  ],
  total: { max: 100, aggregate: "percentAchieved", passAtLeast: 80, requireEveryDomain: false },
  domain: { max: 100, aggregate: "percentAchieved", passAtLeast: 80 },
  labels: {
    passLabel: "Pass (80%)",
    trendSubtitle: "Competency over time",
    domainSubtitle: "Competency rate by domain",
    domainPassLabel: "Pass threshold",
  },
};

export const CASC = {
  rubric: rubric(
    { kind: "boolean", field: "competent", scale: [], step: "number" },
    [
      {
        id: "history",
        kind: "domain",
        title: "History",
        competencies: [
          { id: "assesses_risk", label: "Assesses risk", descriptors: {} },
          { id: "explores_symptoms", label: "Explores symptoms", descriptors: {} },
        ],
        competencyFields: [field("competent", "rating", "rating")],
        fields: [
          field("generic_domains", "group", "other", "Generic domains", [
            field("strengths", "records", "strength", "Strengths", [
              field("strength", "shortText", "strength", "Strength"),
              field("examples", "shortText", "evidence", "Examples"),
            ]),
          ]),
        ],
      },
    ],
    CASC_DISPLAY,
  ),
  result: result(
    {
      history: {
        assesses_risk: { competent: false },
        explores_symptoms: { competent: true },
        generic_domains: { strengths: [{ strength: "Established onset", examples: "\"When did it start?\"" }] },
      },
    },
    {
      total: 20,
      max: 100,
      fraction: 0.2,
      passed: false,
      critical_count: 16,
      domains: [{ id: "history", label: "History", value: 50, counts: {}, passed: false }],
    },
  ),
};

/* ---------- Ortho: 0..10, one of four station types, banded totals ---------- */

export const ORTHO_DISPLAY: Json = {
  bands: [
    { to: 17, from: 0, tone: "poor", label: "" },
    { to: 34, from: 18, tone: "fair", label: "" },
    { to: 42, from: 35, tone: "good", label: "" },
    { to: 50, from: 43, tone: "excellent", label: "" },
  ],
  tones: [
    { tone: "excellent", atLeast: 0.9 },
    { tone: "good", atLeast: 0.7 },
    { tone: "fair", atLeast: 0.4 },
    { tone: "poor", atLeast: 0 },
  ],
  total: { max: 50, aggregate: "sum", passAtLeast: 35, requireEveryDomain: false },
  domain: { max: 10, aggregate: "mean", passAtLeast: 7 },
  labels: {
    passLabel: "Pass (35/50)",
    trendSubtitle: "Station score over time",
    domainSubtitle: "Scores by station type or domain",
    domainPassLabel: "Good (7/10)",
  },
};

const orthoFields = [
  field("score", "rating", "rating"),
  field("score_justification", "longText", "explanation", "Justification"),
  field("completed", "list", "strength", "Completed"),
];

export const ORTHO = {
  rubric: rubric(
    { kind: "range", field: "score", scale: [], minimum: 0, maximum: 10, step: "integer" },
    [
      { kind: "field", field: field("station_type", "shortText", "selector", "Station type") },
      {
        id: "clinical_skills",
        kind: "domain",
        title: "Clinical skills",
        nullable: true,
        fields: [],
        competencies: [{ id: "situational_awareness", label: "Situational awareness", descriptors: {} }],
        competencyFields: orthoFields,
      },
      {
        id: "communication_skills",
        kind: "domain",
        title: "Communication skills",
        nullable: true,
        fields: [],
        competencies: [
          { id: "communication_information_giving", label: "Information giving", descriptors: { "10": "Clear, checked, chunked." } },
        ],
        competencyFields: orthoFields,
      },
    ],
    ORTHO_DISPLAY,
  ),
  result: result(
    {
      station_type: "communication",
      clinical_skills: null,
      communication_skills: {
        communication_information_giving: {
          score: 4,
          score_justification: "Jargon in the explanation.",
          completed: ["Checked understanding once"],
        },
      },
    },
    {
      total: 18,
      max: 50,
      fraction: 0.36,
      passed: false,
      critical_count: 2,
      domains: [{ id: "communication_skills", label: "Communication skills", value: 3.6, counts: {}, passed: false }],
    },
  ),
};

/* ---------- A fifth exam no code knows about ---------- */

export const WARD_ROUND_DISPLAY: Json = {
  bands: [],
  tones: [
    { tone: "good", atLeast: 0.8 },
    { tone: "fair", atLeast: 0.6 },
    { tone: "poor", atLeast: 0 },
  ],
  total: { max: 15, aggregate: "sum", passAtLeast: 9, requireEveryDomain: true },
  domain: { max: 15, aggregate: "sum", passAtLeast: 9 },
  labels: {},
};

export const WARD_ROUND = {
  rubric: rubric(
    { kind: "range", field: "score", scale: [], minimum: 1, maximum: 5, step: "integer" },
    [
      {
        id: "ward_round",
        kind: "domain",
        title: "Ward round",
        competencies: [
          { id: "prioritises", label: "Prioritises the sickest patient", descriptors: {} },
          { id: "delegates", label: "Delegates clearly", descriptors: {} },
          { id: "documents", label: "Documents the plan", descriptors: {} },
        ],
        competencyFields: [
          field("score", "rating", "rating"),
          field("evidence", "list", "evidence", "Evidence"),
          field("missed", "list", "improvement", "Missed"),
        ],
        fields: [field("strengths", "list", "strength", "Strengths")],
      },
      { id: "summary", kind: "section", title: "Summary", fields: [field("narrative", "longText", "explanation", "Narrative")] },
    ],
    WARD_ROUND_DISPLAY,
  ),
  result: result(
    {
      ward_round: {
        prioritises: { score: 4, evidence: ["Saw bed 3 first"], missed: [] },
        delegates: { score: 3, evidence: [], missed: ["Named no owner for bloods"] },
        documents: { score: 2, evidence: [], missed: ["No plan written"] },
        strengths: ["Calm under pressure"],
      },
      summary: { narrative: "A safe round with a thin plan." },
    },
    {
      total: 9,
      max: 15,
      fraction: 0.6,
      passed: true,
      critical_count: 1,
      domains: [{ id: "ward_round", label: "Ward round", value: 9, counts: {}, passed: true }],
    },
  ),
};
