export type ExamShowcaseVariant = "sca" | "plab" | "ortho";

export type SimulationShowcaseContent = {
  examLabel: string;
  stationTitle: string;
  timerLabel: string;
  transcriptRows: Array<{
    speaker: string;
    time: string;
    text: string;
    /** Which side of the transcript the line sits on. */
    side: "them" | "you";
  }>;
  checklistItems: Array<{ label: string; done: boolean }>;
  checklistEyebrow: string;
};

export type ManagementSection = {
  heading: string;
  items: string[];
};

export type ManagementShowcaseContent = {
  title: string;
  subtitle: string;
  sections: ManagementSection[];
};

export type FeedbackDomainRow = {
  domain: string;
  marks: string;
  variant: "competent" | "developing" | "development";
};

export type FeedbackShowcaseContent = {
  stationTitle: string;
  patientSummary: string;
  examMeta: string;
  domains: FeedbackDomainRow[];
  total: string;
};

export type PrioritisationShowcaseContent = {
  title: string;
  subtitle: string;
  cases: Array<{ rank: number; label: string; detail: string; urgent?: boolean }>;
};

export const SIMULATION_SHOWCASE_CONTENT: Record<
  ExamShowcaseVariant,
  SimulationShowcaseContent
> = {
  sca: {
    examLabel: "Station 04 · SCA",
    stationTitle: "Painless jaundice · 62M",
    timerLabel: "07:12 left",
    transcriptRows: [
      {
        speaker: "PATIENT",
        time: "03:41",
        text:
          "My wife says my eyes have gone yellow. I've lost some weight too, but I've been off my food.",
        side: "them",
      },
      {
        speaker: "YOU",
        time: "03:58",
        text:
          "Thank you for telling me. I'd like to ask a few questions, then examine you, and we'll talk through a plan together.",
        side: "you",
      },
      {
        speaker: "PATIENT",
        time: "04:06",
        text: "All right. Should I be worried? My father had something with his bowel.",
        side: "them",
      },
    ],
    checklistItems: [
      { label: "Signposted during the consultation", done: true },
      { label: "Explored weight loss", done: true },
      { label: "Ruled out red flags", done: false },
      { label: "Addressed the family-history concern", done: false },
    ],
    checklistEyebrow: "Athena is marking as you speak",
  },
  plab: {
    examLabel: "Station 08 · PLAB 2",
    stationTitle: "Acute anaphylaxis · 32F",
    timerLabel: "06:40 left",
    transcriptRows: [
      {
        speaker: "PATIENT",
        time: "01:12",
        text:
          "I ate peanuts about ten minutes ago. My lips are tingling and I feel tight in my chest.",
        side: "them",
      },
      {
        speaker: "YOU",
        time: "01:28",
        text:
          "I'm going to assess you quickly, call for help, and start treatment straight away.",
        side: "you",
      },
      {
        speaker: "PATIENT",
        time: "01:35",
        text: "I'm getting wheezy. I have an EpiPen but I've never used it.",
        side: "them",
      },
    ],
    checklistItems: [
      { label: "Called for emergency help", done: true },
      { label: "Assessed airway and breathing", done: true },
      { label: "Administered IM adrenaline", done: false },
      { label: "Explained next steps clearly", done: false },
    ],
    checklistEyebrow: "Live marking against PLAB domains",
  },
  ortho: {
    examLabel: "Clinical · Ortho ST3",
    stationTitle: "Open tibial fracture · 34M",
    timerLabel: "06:40 left",
    transcriptRows: [
      {
        speaker: "INTERVIEWER",
        time: "01:12",
        text:
          "This patient has an open tibial fracture. Walk me through your initial assessment and immediate management.",
        side: "them",
      },
      {
        speaker: "YOU",
        time: "01:28",
        text:
          "I'd follow ATLS, classify the injury with Gustilo-Anderson, give IV antibiotics within one hour per BOAST, and arrange urgent orthoplastic review.",
        side: "you",
      },
      {
        speaker: "INTERVIEWER",
        time: "02:05",
        text:
          "Good. What imaging do you need before theatre, and what would influence your fixation plan?",
        side: "them",
      },
    ],
    checklistItems: [
      { label: "Applied ATLS priorities", done: true },
      { label: "Classified Gustilo-Anderson", done: true },
      { label: "Antibiotics within the hour", done: false },
      { label: "Planned orthoplastic review", done: false },
    ],
    checklistEyebrow: "Clinical station marks",
  },
};

export const MANAGEMENT_SHOWCASE_CONTENT: Record<
  "sca" | "plab",
  ManagementShowcaseContent
> = {
  sca: {
    title: "Low mood in primary care",
    subtitle: "Evidence-based plan aligned to NICE CG90",
    sections: [
      {
        heading: "Immediate actions",
        items: [
          "Assess suicide and self-harm risk directly",
          "Screen for bipolar disorder before starting antidepressants",
          "Offer same-day follow-up if risk is elevated",
        ],
      },
      {
        heading: "Investigations",
        items: [
          "TFTs, FBC, glucose, U&Es, LFTs, calcium",
          "Consider HbA1c if metabolic risk factors present",
        ],
      },
      {
        heading: "Management",
        items: [
          "Low-intensity psychological intervention for mild depression",
          "SSRI if moderate/severe or patient preference",
          "Discuss side effects, review at 2 weeks",
        ],
      },
      {
        heading: "Safety netting",
        items: [
          "Crisis line and same-day contact if thoughts worsen",
          "Review in 2 weeks, then 4–6 weeks after starting treatment",
        ],
      },
    ],
  },
  plab: {
    title: "Suspected anaphylaxis",
    subtitle: "Structured emergency management outline",
    sections: [
      {
        heading: "Immediate actions",
        items: [
          "Remove trigger if still present",
          "Call for help and monitor ABCDE",
          "Lie flat with legs raised unless breathing difficulty",
        ],
      },
      {
        heading: "Treatment",
        items: [
          "IM adrenaline 0.5 mg (1:1000) into anterolateral thigh",
          "Repeat at 5 minutes if no improvement",
          "High-flow oxygen and IV fluid bolus if shocked",
        ],
      },
      {
        heading: "Monitoring",
        items: [
          "Continuous observations for minimum 6–12 hours",
          "Document time of adrenaline doses",
          "Arrange allergy clinic referral before discharge",
        ],
      },
      {
        heading: "Safety netting",
        items: [
          "Issue two adrenaline auto-injectors with training",
          "Provide written anaphylaxis action plan",
        ],
      },
    ],
  },
};

export const FEEDBACK_SHOWCASE_CONTENT: Record<
  "sca" | "plab",
  FeedbackShowcaseContent
> = {
  sca: {
    stationTitle: "Low mood",
    patientSummary: "34F · new presentation",
    examMeta: "RCGP SCA · 12 minutes, timed",
    domains: [
      {
        domain: "Data gathering & diagnosis",
        marks: "7 / 9",
        variant: "competent",
      },
      {
        domain: "Clinical management",
        marks: "6 / 9",
        variant: "competent",
      },
      {
        domain: "Relating to others",
        marks: "5 / 9",
        variant: "developing",
      },
    ],
    total: "18 / 27",
  },
  plab: {
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
};

export const PRIORITISATION_SHOWCASE_CONTENT: PrioritisationShowcaseContent = {
  title: "Trauma list prioritisation",
  subtitle: "Rank cases by clinical urgency before the panel",
  cases: [
    {
      rank: 1,
      label: "Open femoral fracture with haemorrhage",
      detail: "Requires immediate resus and ortho review",
      urgent: true,
    },
    {
      rank: 2,
      label: "Displaced ankle fracture · neurovascular compromise",
      detail: "Urgent reduction before swelling progresses",
      urgent: true,
    },
    {
      rank: 3,
      label: "Stable radial head fracture",
      detail: "Can wait for next available trauma list slot",
    },
    {
      rank: 4,
      label: "Chronic rotator cuff symptoms",
      detail: "Suitable for routine outpatient review",
    },
  ],
};
