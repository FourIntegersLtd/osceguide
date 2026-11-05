import type { Surface } from "@/capabilities/surface";

/** The words a screen says for the same things in an institution and in an employer workspace. */
export type AssessWords = {
  sitting: string;
  sittings: string;
  Sitting: string;
  Sittings: string;
  trainee: string;
  trainees: string;
  Trainee: string;
  Trainees: string;
  People: string;
  scheduleSitting: string;
  addPeople: string;
  /** The thing examined and marked: an exam in both arms. */
  exam: string;
  exams: string;
  Exam: string;
  Exams: string;
  /** The template a station takes, shown as "Station layout (optional)". */
  stationLayout: string;
  StationLayout: string;
  StationLayouts: string;
  /** The people who run a circuit and review it: supervisors, assessors for an employer. */
  supervisor: string;
  supervisors: string;
  Supervisor: string;
  Supervisors: string;
  /** A cohort: the whole intake that is scheduled in one step. */
  yearGroup: string;
  yearGroups: string;
  YearGroup: string;
  YearGroups: string;
  /** A free-form set of people, distinct from a year group. */
  group: string;
  groups: string;
  Group: string;
  Groups: string;
  /** What a sitting's mode is called: the words that replace the clash with "Exam". */
  kind: string;
  formalExam: string;
  training: string;
};

export const INSTITUTION_WORDS: AssessWords = {
  sitting: "sitting",
  sittings: "sittings",
  Sitting: "Sitting",
  Sittings: "Sittings",
  trainee: "trainee",
  trainees: "trainees",
  Trainee: "Trainee",
  Trainees: "Trainees",
  People: "People",
  scheduleSitting: "Schedule a sitting",
  addPeople: "Add people",
  exam: "exam",
  exams: "exams",
  Exam: "Exam",
  Exams: "Exams",
  stationLayout: "station layout",
  StationLayout: "Station layout",
  StationLayouts: "Station layouts",
  supervisor: "supervisor",
  supervisors: "supervisors",
  Supervisor: "Supervisor",
  Supervisors: "Supervisors",
  yearGroup: "year group",
  yearGroups: "year groups",
  YearGroup: "Year group",
  YearGroups: "Year groups",
  group: "group",
  groups: "groups",
  Group: "Group",
  Groups: "Groups",
  kind: "Kind",
  formalExam: "Formal exam",
  training: "Training",
};

export const EMPLOYER_WORDS: AssessWords = {
  sitting: "assessment",
  sittings: "assessments",
  Sitting: "Assessment",
  Sittings: "Assessments",
  trainee: "candidate",
  trainees: "candidates",
  Trainee: "Candidate",
  Trainees: "Candidates",
  People: "Candidates",
  scheduleSitting: "Schedule an assessment",
  addPeople: "Add candidates",
  exam: "exam",
  exams: "exams",
  Exam: "Exam",
  Exams: "Exams",
  stationLayout: "station layout",
  StationLayout: "Station layout",
  StationLayouts: "Station layouts",
  supervisor: "assessor",
  supervisors: "assessors",
  Supervisor: "Assessor",
  Supervisors: "Assessors",
  yearGroup: "intake",
  yearGroups: "intakes",
  YearGroup: "Intake",
  YearGroups: "Intakes",
  group: "group",
  groups: "groups",
  Group: "Group",
  Groups: "Groups",
  kind: "Kind",
  formalExam: "Formal exam",
  training: "Training",
};

/** Employer words in a hire workspace, institution words everywhere else. */
export function assessWordsFor(surface: Surface | undefined): AssessWords {
  return surface === "hire" ? EMPLOYER_WORDS : INSTITUTION_WORDS;
}
