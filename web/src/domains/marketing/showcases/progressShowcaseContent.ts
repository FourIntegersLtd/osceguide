import type { ExamShowcaseVariant } from "./examShowcaseContent";

/** A three-way RAG split. The three values are percentages and must total 100. */
export type ProgressRagSplit = {
  competent: number;
  developing: number;
  development: number;
};

export type ProgressDomainRow = {
  label: string;
  split: ProgressRagSplit;
};

export type ProgressCategoryPoint = {
  /** Rendered as one SVG line per entry, so the label wraps where you split it. */
  labelLines: string[];
  value: number;
};

export type ProgressShowcaseContent = {
  eyebrow: string;
  title: string;
  subtitle: string;
  examDateLabel: string;
  ctaLabel: string;
  competency: ProgressRagSplit;
  /**
   * Eight weekly competent percentages, oldest first. Use 0 for a week with no
   * assessed marks — those render as the muted "no data" stub.
   */
  weeklyTrend: number[];
  domains: ProgressDomainRow[];
  categories: ProgressCategoryPoint[];
  /** Top of the category axis. Keep it a round number — it also sets the ticks. */
  categoryAxisMax: number;
  /** Shown under the frame so the numbers are never mistaken for a real account. */
  caption: string;
};

export const PROGRESS_SHOWCASE_CONTENT: Record<
  ExamShowcaseVariant,
  ProgressShowcaseContent
> = {
  sca: {
    eyebrow: "31 stations attempted",
    title: "Where you stand",
    subtitle: "Six weeks to your sitting. Tasks is the domain to work on.",
    examDateLabel: "6 weeks to go",
    ctaLabel: "Practise a station",
    competency: { competent: 14, developing: 29, development: 57 },
    weeklyTrend: [9, 0, 0, 0, 12, 10, 19, 14],
    domains: [
      {
        label: "Global skills",
        split: { development: 37, developing: 38, competent: 25 },
      },
      {
        label: "Relating to others",
        split: { development: 59, developing: 28, competent: 13 },
      },
      {
        label: "Tasks",
        split: { development: 66, developing: 24, competent: 10 },
      },
    ],
    categories: [
      { labelLines: ["Task", "Management"], value: 112 },
      { labelLines: ["Communication", "Skills"], value: 87 },
      { labelLines: ["Consultation", "Skills"], value: 84 },
    ],
    categoryAxisMax: 120,
    caption: "Example dashboard. Figures are illustrative.",
  },
  plab: {
    eyebrow: "24 stations attempted",
    title: "Where you stand",
    subtitle: "Data gathering is steady. History taking needs the work.",
    examDateLabel: "9 weeks to go",
    ctaLabel: "Practise a station",
    competency: { competent: 22, developing: 34, development: 44 },
    weeklyTrend: [11, 0, 0, 14, 17, 15, 26, 22],
    domains: [
      {
        label: "Data gathering",
        split: { development: 31, developing: 36, competent: 33 },
      },
      {
        label: "Clinical management",
        split: { development: 48, developing: 31, competent: 21 },
      },
      {
        label: "Interpersonal skills",
        split: { development: 52, developing: 30, competent: 18 },
      },
    ],
    categories: [
      { labelLines: ["History", "Taking"], value: 94 },
      { labelLines: ["Examination", "Skills"], value: 71 },
      { labelLines: ["Counselling", "Skills"], value: 66 },
    ],
    categoryAxisMax: 100,
    caption: "Example dashboard. Figures are illustrative.",
  },
  ortho: {
    eyebrow: "18 stations attempted",
    title: "Where you stand",
    subtitle: "Assessment is coming along. Operative planning is behind it.",
    examDateLabel: "11 weeks to go",
    ctaLabel: "Practise a station",
    competency: { competent: 27, developing: 35, development: 38 },
    weeklyTrend: [13, 0, 0, 0, 19, 21, 31, 27],
    domains: [
      {
        label: "Assessment",
        split: { development: 29, developing: 34, competent: 37 },
      },
      {
        label: "Operative planning",
        split: { development: 44, developing: 33, competent: 23 },
      },
      {
        label: "Professionalism",
        split: { development: 35, developing: 38, competent: 27 },
      },
    ],
    categories: [
      { labelLines: ["Trauma", "Management"], value: 68 },
      { labelLines: ["Elective", "Planning"], value: 54 },
      { labelLines: ["Communication", "Skills"], value: 49 },
    ],
    categoryAxisMax: 80,
    caption: "Example dashboard. Figures are illustrative.",
  },
};

export function getProgressShowcaseContent(
  variant: ExamShowcaseVariant = "sca",
): ProgressShowcaseContent {
  return PROGRESS_SHOWCASE_CONTENT[variant];
}
