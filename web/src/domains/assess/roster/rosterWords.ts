import type { AssessWords } from "@/capabilities/assess-words/vocabulary";


/** Whole phrases that mention sitting, which a word swap would turn into "assessment". */
const HIRE_PHRASES: readonly (readonly [string, string])[] = [
  ["Stop them sitting or signing in.", "Stop them taking assessments or signing in."],
  ["Let them sit and sign in again.", "Let them take assessments and sign in again."],
  ["will not be able to sign in or sit anything", "will not be able to sign in or take any assessment"],
  ["will be able to sign in and sit again.", "will be able to take assessments and sign in again."],
  ["is already on this roster.", "is already a candidate."],
  ["already on the roster", "already a candidate"],
  ["Ask one of them to add the people you need on the roster.", "Ask one of them to add the candidates you need."],
];

/**
 * A roster sentence written in institution words, said in the workspace's words. An institution
 * gets the text back byte for byte; an employer gets candidate, intake and no roster.
 */
export function say(w: AssessWords, text: string): string {
  if (!w.hiring) return text;
  let out = HIRE_PHRASES.reduce((acc, [from, to]) => acc.split(from).join(to), text);
  out = out
    .replace(/\bTrainees\b/g, w.Trainees)
    .replace(/\bTrainee\b/g, w.Trainee)
    .replace(/\btrainees\b/g, w.trainees)
    .replace(/\btrainee\b/g, w.trainee)
    .replace(/\bYear groups\b/g, w.YearGroups)
    .replace(/\bYear group\b/g, w.YearGroup)
    .replace(/\byear groups\b/g, w.yearGroups)
    .replace(/\byear group\b/g, w.yearGroup)
    .replace(/\bpeople\b/g, w.trainees)
    .replace(/\bperson\b/g, w.trainee)
    .replace(/\bthe roster\b/g, "the candidate list")
    .replace(/\bthis roster\b/g, "this candidate list");
  return out;
}
