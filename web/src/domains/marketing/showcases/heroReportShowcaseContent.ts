import type { ExamShowcaseVariant, FeedbackDomainRow } from "./examShowcaseContent";

export type HeroReportShowcaseContent = {
  backLeft: {
    stationTitle: string;
    patientSummary: string;
  };
  backRight: {
    marks: string;
    totalPercent: string;
  };
  front: {
    stationTitle: string;
    patientSummary: string;
    examMeta: string;
    domains: FeedbackDomainRow[];
    total: string;
  };
};

export const HERO_REPORT_SHOWCASE_CONTENT: Record<
  ExamShowcaseVariant,
  HeroReportShowcaseContent
> = {
  sca: {
    backLeft: {
      stationTitle: "Low mood",
      patientSummary: "34F · new presentation",
    },
    backRight: {
      marks: "21 / 27",
      totalPercent: "78%",
    },
    front: {
      stationTitle: "Painless jaundice",
      patientSummary: "62M · new presentation",
      examMeta: "RCGP SCA · 12 minutes, timed",
      domains: [
        {
          domain: "Data gathering & diagnosis",
          marks: "7 / 9",
          variant: "competent",
        },
        {
          domain: "Clinical management",
          marks: "5 / 9",
          variant: "developing",
        },
        {
          domain: "Relating to others",
          marks: "3 / 9",
          variant: "development",
        },
      ],
      total: "15 / 27",
    },
  },
  plab: {
    backLeft: {
      stationTitle: "Breaking bad news",
      patientSummary: "58M · lung cancer diagnosis",
    },
    backRight: {
      marks: "19 / 24",
      totalPercent: "79%",
    },
    front: {
      stationTitle: "Acute anaphylaxis",
      patientSummary: "32F · peanut exposure",
      examMeta: "PLAB 2 · 8 minutes, timed",
      domains: [
        {
          domain: "Data gathering",
          marks: "6 / 8",
          variant: "competent",
        },
        {
          domain: "Clinical management",
          marks: "5 / 8",
          variant: "developing",
        },
        {
          domain: "Interpersonal skills",
          marks: "7 / 8",
          variant: "competent",
        },
      ],
      total: "18 / 24",
    },
  },
  ortho: {
    backLeft: {
      stationTitle: "Trauma prioritisation",
      patientSummary: "Mixed list · 4 cases",
    },
    backRight: {
      marks: "35 / 50",
      totalPercent: "70%",
    },
    front: {
      stationTitle: "Open tibial fracture",
      patientSummary: "Clinical scenario · trauma",
      examMeta: "Orthopaedic ST3 · 10 minutes · 2 interviewers",
      domains: [
        {
          domain: "Technical Knowledge & Clinical Expertise",
          marks: "8 / 10",
          variant: "competent",
        },
        {
          domain: "Situational Awareness",
          marks: "7 / 10",
          variant: "competent",
        },
        {
          domain: "Communication - Information Gathering",
          marks: "7 / 10",
          variant: "competent",
        },
        {
          domain: "Problem Solving & Decision Making",
          marks: "6 / 10",
          variant: "developing",
        },
        {
          domain: "Communication - Information Giving",
          marks: "7 / 10",
          variant: "competent",
        },
      ],
      total: "35 / 50",
    },
  },
};

export function getHeroReportShowcaseContent(
  variant: ExamShowcaseVariant = "sca",
): HeroReportShowcaseContent {
  return HERO_REPORT_SHOWCASE_CONTENT[variant];
}
