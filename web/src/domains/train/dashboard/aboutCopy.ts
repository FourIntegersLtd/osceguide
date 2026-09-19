import {
  type AboutContent,
  type AboutItem,
  type AboutKey,
  type ExamAbout,
  LEARNING_JOURNEY,
} from "@/domains/train/dashboard/aboutTypes";

/**
 * What the three "about" modals say, per exam.
 *
 * The old dashboards each shipped their own `SummaryCardInfo`, `DomainInfo`
 * and `TrendInfo` — three components times four exams, identical in structure
 * and different only in the sentences. They are sentences, so they live in a
 * table; `AboutModals` renders them with the same `AboutInfo` primitives the
 * originals used.
 */

export type { AboutContent, AboutItem, AboutKey, ExamAbout };

const PLAB_ABOUT: ExamAbout = {
  summary: LEARNING_JOURNEY(
    "PLAB",
    "Stations where you demonstrated confident competency (≥7/12 with ≥2/4 in each domain). These show your strengths and areas where you're exam-ready.",
  ),
  domain: {
    title: "Domain performance",
    description:
      "This chart shows your average performance across the three PLAB assessment domains.",
    sectionTitle: "Assessment domains",
    sectionTone: "sky",
    items: [
      {
        marker: "swatch",
        swatchFor: "Data Gathering",
        title: "Data Gathering",
        description:
          "Includes history taking, examination skills, ordering appropriate investigations, and clinical interpretation.",
      },
      {
        marker: "swatch",
        swatchFor: "Clinical Management",
        title: "Clinical Management",
        description:
          "Includes diagnosis accuracy, treatment plans, safety netting, and follow-up arrangements.",
      },
      {
        marker: "swatch",
        swatchFor: "Interpersonal Skills",
        title: "Interpersonal Skills",
        description:
          "Includes language clarity, listening skills, rapport building, and empathy demonstration.",
      },
    ],
    callout: {
      label: "Note",
      text: "The amber line at score 2.0 indicates the minimum threshold required in each domain to pass a station.",
    },
  },
  trend: {
    title: "Performance trend",
    description:
      "This chart tracks your total station scores over time, allowing you to monitor your progress.",
    sectionTitle: "How to read the chart",
    sectionTone: "amber",
    items: [
      {
        marker: "plain",
        title: "Station scores",
        description: "Each point represents your total score (out of 12) for a completed station.",
      },
      {
        marker: "threshold",
        title: "Pass threshold",
        description:
          "The green line at score 7.0 indicates the minimum total threshold required to pass a station.",
      },
    ],
    callout: {
      label: "Tip",
      text: "Look for upward trends that indicate improvement. If your scores are consistently near or above the green line, you're on track for success in the PLAB exam.",
    },
  },
};

const CASC_ABOUT: ExamAbout = {
  summary: {
    title: "Performance summary",
    description:
      "This section shows your overall performance across all completed CASC stations.",
    sectionTitle: "What the rates mean",
    sectionTone: "sky",
    items: [
      {
        marker: "success",
        title: "Pass rate",
        description:
          "Percentage of stations where you achieved at least 80% competency in each domain (History Taking, Examination, Management, and Communication).",
      },
      {
        marker: "danger",
        title: "Fail rate",
        description:
          "Percentage of stations where competency requirements were not met in one or more domains.",
      },
    ],
  },
  domain: {
    title: "Domain performance",
    description:
      "This chart shows your average competency rate across the four CASC assessment domains.",
    sectionTitle: "Assessment domains",
    sectionTone: "sky",
    items: ["History Taking", "Examination", "Management", "Communication"].map((domain) => ({
      marker: "swatch" as const,
      swatchFor: domain,
      title: domain,
      description:
        "Shows the percentage of competencies achieved within this domain across all stations.",
    })),
    callout: {
      label: "Note",
      text: "The amber line at 80% indicates the minimum competency threshold required in each domain to pass a station.",
    },
  },
  trend: {
    title: "Performance trend",
    description:
      "This chart tracks your overall competency rate over time across all domains.",
    sectionTitle: "How to read the chart",
    sectionTone: "amber",
    items: [
      {
        marker: "plain",
        title: "Competency rate",
        description:
          "Each point represents your overall competency rate for a completed station.",
      },
      {
        marker: "threshold",
        title: "Pass threshold",
        description:
          "The green line at 80% indicates the minimum competency rate required to pass.",
      },
    ],
  },
};

const ORTHO_ABOUT: ExamAbout = {
  summary: {
    ...LEARNING_JOURNEY(
      "orthopaedic ST3 interview",
      "Stations where you demonstrated confident competency (≥35/50). These show your strengths and where you're interview-ready.",
    ),
    callout: {
      label: "Remember",
      text: "Every expert was once a beginner. Focus on progress, not perfection.",
    },
  },
  domain: {
    title: "Domain performance",
    description:
      "This chart groups your performance by station type, showing average scores across core competency domains.",
    sectionTitle: "Station types",
    sectionTone: "sky",
    items: [
      {
        marker: "plain",
        title: "Clinical stations",
        description: "Technical knowledge, clinical reasoning, patient assessment.",
      },
      {
        marker: "plain",
        title: "Prioritisation stations",
        description: "Organisation, time management, decision-making under pressure.",
      },
      {
        marker: "plain",
        title: "Communication stations",
        description:
          "Information exchange, situational awareness, professional communication.",
      },
    ],
    callout: {
      label: "How to read",
      text: "Each station type shows grouped bars for different competency areas. Higher bars indicate stronger performance. Aim for scores above 7/10 across all domains for confident interview performance.",
    },
  },
  trend: {
    title: "Performance trend",
    description:
      "This chart tracks your total station scores over time across different station types so you can monitor progress.",
    sectionTitle: "How to read the chart",
    sectionTone: "amber",
    items: [
      {
        marker: "plain",
        title: "Station scores",
        description: "Each point is your total score (out of 50) for a completed station.",
      },
      {
        marker: "threshold",
        title: "Pass threshold",
        description:
          "The green line at score 35 is the minimum total threshold (70%) to pass a station in the ST3 interview.",
      },
    ],
    callout: {
      label: "Tip",
      text: "Look for upward trends. Consistently scoring above the green line across station types shows you're ready for your ST3 interview.",
    },
  },
};

const SCA_ABOUT: ExamAbout = {
  summary: {
    title: "Your competency mix",
    description:
      "How your assessed marks split across the three levels, across every SCA station you have completed.",
    sectionTitle: "The three levels",
    sectionTone: "sky",
    items: [
      {
        marker: "success",
        title: "Competent",
        description: "Marks that meet the standard expected in the exam.",
      },
      {
        marker: "plain",
        title: "Developing",
        description: "Marks on their way there — the quickest ground to make up.",
      },
      {
        marker: "danger",
        title: "Development",
        description: "Marks that need work. Practise these areas next.",
      },
    ],
  },
  domain: {
    title: "Domains",
    description: "Each bar shows how much of your work in that area met the competent standard.",
    sectionTitle: "The three areas",
    sectionTone: "sky",
    items: [
      {
        marker: "swatch",
        swatchFor: "Global skills",
        title: "Global skills",
        description: "How you run the consultation: structure, timing, ethics, and clarity.",
      },
      {
        marker: "swatch",
        swatchFor: "Tasks",
        title: "Tasks",
        description: "The clinical work: history, examination, diagnosis, and plan.",
      },
      {
        marker: "swatch",
        swatchFor: "Relating to others",
        title: "Relating to others",
        description:
          "How you connect with the patient: listening, empathy, and shared decisions.",
      },
    ],
    callout: {
      label: "Note",
      text: "A good consultation needs all three areas. Look at your weakest bar and practise that next.",
    },
  },
  trend: {
    title: "Performance trend",
    description: "This chart tracks the share of your marks meeting the competent standard.",
    sectionTitle: "How to read the chart",
    sectionTone: "amber",
    items: [
      {
        marker: "plain",
        title: "Competency rate",
        description: "Each point is one station's share of competent marks.",
      },
      {
        marker: "plain",
        title: "Direction matters",
        description:
          "A rising line is what to aim for; a single low station is not a verdict.",
      },
    ],
  },
};

export const EXAM_ABOUT: Record<string, ExamAbout> = {
  sca: SCA_ABOUT,
  plab: PLAB_ABOUT,
  casc: CASC_ABOUT,
  ortho: ORTHO_ABOUT,
};

export function aboutFor(examCode: string): ExamAbout {
  return EXAM_ABOUT[examCode.toLowerCase()] ?? PLAB_ABOUT;
}
