/**
 * What a programme can be for.
 *
 * Product copy, not data: the five purposes and what each one sets up are the
 * same for every organisation. The backend has no `purpose` column yet, so
 * nothing here is read from or written to the API.
 */
export type ProgrammePurpose =
  | "exam_preparation"
  | "placement"
  | "recruitment"
  | "onboarding"
  | "cpd";

export interface PurposeCopy {
  id: ProgrammePurpose;
  label: string;
  /** Where in a career it sits, such as "Before the exam". */
  when: string;
  headline: string;
  stages: readonly [string, string, string];
  /** What the people in it are called, singular and plural. */
  person: readonly [string, string];
  addLabel: string;
  /** The second date on the new-programme form. */
  milestoneLabel: string;
  setsUp: {
    whoJoins: string;
    marking: string;
    stages: string;
    outcome: string;
    stations: string;
  };
}

export const PURPOSES: readonly PurposeCopy[] = [
  {
    id: "exam_preparation",
    label: "Exam preparation",
    when: "Before the exam",
    headline: "Prepare trainees for their licensing exam",
    stages: ["Practise stations", "Sit mock exams", "Release signed-off results"],
    person: ["trainee", "trainees"],
    addLabel: "Add trainees",
    milestoneLabel: "Exam date",
    setsUp: {
      whoJoins: "Trainees, invited by email or your organisation's sign-in",
      marking: "Marked against the exam's rubric. Examiners review and a lead signs off before release.",
      stages: "Practise stations on their own, sit mock exams in circuits, then read a signed-off result.",
      outcome: "A released result for each sitting",
      stations: "The published stations for the exam you choose",
    },
  },
  {
    id: "placement",
    label: "Placement preparation",
    when: "Before patient contact",
    headline: "Prepare students for clinical placements",
    stages: ["Build confidence", "Practise safely", "Prepare for real clinical encounters"],
    person: ["student", "students"],
    addLabel: "Add students",
    milestoneLabel: "First patient contact",
    setsUp: {
      whoJoins: "Students, invited by email or your university sign-in",
      marking:
        "Practice only. Feedback goes to the student. Tutors see progress and readiness, not a mark on the record.",
      stages:
        "Build confidence with short stations, practise safely in tutor sessions, then a readiness check before the first patient.",
      outcome: "A readiness summary to take into placement",
      stations: "Taking a history, explaining a result, escalating a deteriorating patient, consent",
    },
  },
  {
    id: "recruitment",
    label: "Recruitment",
    when: "Before appointment",
    headline: "Add clinical skills to recruitment",
    stages: ["Structured assessment", "Role-relevant scenarios", "More informed interviews"],
    person: ["candidate", "candidates"],
    addLabel: "Invite candidates",
    milestoneLabel: "Interviews start",
    setsUp: {
      whoJoins: "Candidates, by a link in their invitation email. No account needed.",
      marking: "No score and no recommendation. Findings are shown as did well, needs improving and not done.",
      stages: "Candidates sit the stations, your panel reviews the findings, then interviews follow up on them.",
      outcome: "An interview pack for each reviewed candidate",
      stations: "Scenarios that match the role you are appointing to",
    },
  },
  {
    id: "onboarding",
    label: "Onboarding",
    when: "After appointment",
    headline: "Support international clinician onboarding",
    stages: ["Understand expectations", "Adapt communication", "Transition into NHS practice"],
    person: ["new starter", "new starters"],
    addLabel: "Add new starters",
    milestoneLabel: "Independent clinics from",
    setsUp: {
      whoJoins: "New starters, invited by email",
      marking: "Practice with feedback. A supervisor signs off each stage.",
      stages: "Learn how a consultation is expected to run, adapt communication, then move into independent practice.",
      outcome: "A sign-off for independent clinics",
      stations: "Consultation structure, shared decisions, safety-netting, remote consultations",
    },
  },
  {
    id: "cpd",
    label: "Continuous development",
    when: "Throughout practice",
    headline: "Make skills development continuous",
    stages: ["New guidance", "New skills", "Ongoing professional development"],
    person: ["member of staff", "staff"],
    addLabel: "Add staff",
    milestoneLabel: "Review date",
    setsUp: {
      whoJoins: "Your clinical staff, invited by email or your organisation's sign-in",
      marking: "Practice only. Completed practice is logged with time and a short reflection.",
      stages: "When guidance changes, a short set of stations follows and everyone gets them as their next practice.",
      outcome: "A CPD record and a certificate for appraisal",
      stations: "Generated from each guidance update you add",
    },
  },
];

const BY_ID = Object.fromEntries(PURPOSES.map((entry) => [entry.id, entry])) as Record<
  ProgrammePurpose,
  PurposeCopy
>;

export function purposeCopy(purpose: ProgrammePurpose): PurposeCopy {
  return BY_ID[purpose];
}
