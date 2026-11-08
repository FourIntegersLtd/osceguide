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
  /** A cohort: the intake an employer hires in. */
  cohort: string;
  cohorts: string;
  Cohort: string;
  Cohorts: string;
  /** True in a hire workspace, where results are hiring decisions. */
  hiring: boolean;
  /** The button to the live board from the running-now card. */
  liveBoardLink: string;
  /** What a sitting's mode is called, so it never clashes with the "Exam" noun. */
  formalExam: string;
  training: string;
  /** A circuit: a rotation for an employer. */
  circuit: string;
  circuits: string;
  Circuit: string;
  Circuits: string;
  /** The landing screen. */
  Home: string;
  /** What a candidate's own list is called. */
  MyTraining: string;
  /** The reviewer above the examiners: a lead assessor for an employer. */
  leadSupervisor: string;
  LeadSupervisor: string;
  /** The person who marks a station and reads its notes: an examiner, an assessor for an employer. */
  examiner: string;
  examiners: string;
  Examiner: string;
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
  supervisor: "supervisor",
  supervisors: "supervisors",
  Supervisor: "Supervisor",
  Supervisors: "Supervisors",
  yearGroup: "year group",
  yearGroups: "year groups",
  YearGroup: "Year group",
  YearGroups: "Year groups",
  cohort: "cohort",
  cohorts: "cohorts",
  Cohort: "Cohort",
  Cohorts: "Cohorts",
  hiring: false,
  liveBoardLink: "Open the live board",
  formalExam: "Formal exam",
  training: "Training",
  circuit: "circuit",
  circuits: "circuits",
  Circuit: "Circuit",
  Circuits: "Circuits",
  Home: "Home",
  MyTraining: "My training",
  leadSupervisor: "GP lead",
  LeadSupervisor: "GP lead",
  examiner: "examiner",
  examiners: "examiners",
  Examiner: "Examiner",
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
  supervisor: "assessor",
  supervisors: "assessors",
  Supervisor: "Assessor",
  Supervisors: "Assessors",
  yearGroup: "intake",
  yearGroups: "intakes",
  YearGroup: "Intake",
  YearGroups: "Intakes",
  cohort: "intake",
  cohorts: "intakes",
  Cohort: "Intake",
  Cohorts: "Intakes",
  hiring: true,
  liveBoardLink: "Watch it",
  formalExam: "Formal exam",
  training: "Training",
  circuit: "rotation",
  circuits: "rotations",
  Circuit: "Rotation",
  Circuits: "Rotations",
  Home: "Overview",
  MyTraining: "My assessments",
  leadSupervisor: "lead assessor",
  LeadSupervisor: "Lead assessor",
  examiner: "assessor",
  examiners: "assessors",
  Examiner: "Assessor",
};

/** Employer words in a hire workspace, institution words everywhere else. */
export function assessWordsFor(surface: Surface | undefined): AssessWords {
  return surface === "hire" ? EMPLOYER_WORDS : INSTITUTION_WORDS;
}

/** "a rotation", "an assessment": the indefinite article for a word from `AssessWords`. */
export function aOrAn(word: string, capital = false): string {
  const article = /^[aeiou]/i.test(word) ? "an" : "a";
  return `${capital ? article.replace(/^./, (c) => c.toUpperCase()) : article} ${word}`;
}
