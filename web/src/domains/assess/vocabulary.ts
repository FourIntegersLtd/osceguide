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
};

/** Employer words in a hire workspace, institution words everywhere else. */
export function assessWordsFor(surface: Surface | undefined): AssessWords {
  return surface === "hire" ? EMPLOYER_WORDS : INSTITUTION_WORDS;
}
