/** The sentences the authoring screens say about people, scheduling and kinds of exam, in the workspace's words. */

import type { AssessWords } from "@/capabilities/assess-words/vocabulary";

/** A hire workspace says "Available" where an institution says "Ready to schedule". */
export function examChipLabel(chip: string, w: AssessWords): string {
  return w.hiring && chip === "Ready to schedule" ? "Available" : chip;
}

export const examEmptyBody = (w: AssessWords) =>
  w.hiring
    ? "Start from one of ours, or build your own. You need one before you can schedule an assessment."
    : `Create an exam, attach a marking scheme version, then publish it to run ${w.sittings} against it.`;

export const programmeLead = (w: AssessWords) =>
  `A programme groups this ${w.hiring ? "organisation" : "institution"}'s ${w.sittings} under one exam.`;

export const programmeEmptyTitle = (w: AssessWords) => (w.hiring ? "No exams offered yet" : "No programmes yet");

export const programmeEmptyBody = (w: AssessWords) =>
  w.hiring
    ? "Switch an exam on to offer it when you schedule an assessment."
    : `Add a programme for each exam you run ${w.sittings} against.`;

export const authoringLead = (w: AssessWords) =>
  w.hiring
    ? "What you assess candidates on: the stations and how they are marked."
    : "Everything you examine with: the exams themselves, their stations, how they are marked, the layout a station follows, and which exams are offered for scheduling.";

export const stationsLead = (w: AssessWords) =>
  w.hiring
    ? "The scenarios candidates work through. Each has a patient, a brief and the marking it uses."
    : "Published station cases for sessions and practice.";

export const importLabel = (w: AssessWords) => (w.hiring ? "Import a document" : "Import from PDF or Word");

export const stationBuilderLead = (w: AssessWords) =>
  w.hiring ? `Write the brief, the patient and the ${w.examiner}'s notes. Publish when it reads right.` : null;

export const briefHelp = (w: AssessWords) =>
  w.hiring
    ? `The candidate sees this in their ${w.sitting} page before the station starts.`
    : "What the candidate reads before the station starts. Saving this does not cut a new version.";

export const addPhotoLabel = (w: AssessWords) => (w.hiring ? "Add a photo" : "Add");

export const generateDraftHeading = (w: AssessWords) => (w.hiring ? "What is it about?" : "Generate draft");

export const generateDraftHelp = (w: AssessWords) =>
  w.hiring
    ? "We write a first draft you then edit. Nothing is published until you press Publish."
    : "Paste a short prompt (a few lines). We\u2019ll auto-fill the template fields below; you can edit anything afterward.";

/** The title and helper a station section shows for the notes only the marker reads; null where the layout's own wording stands. */
export function examinerSectionNote(title: string, w: AssessWords): { title: string; help: string } | null {
  return w.hiring
    ? { title: /examiner|assessor/i.test(title) || title.trim() === "" ? `${w.Examiner}'s notes` : title, help: `${w.Examiner}s see these on the marking page. Candidates never do.` }
    : null;
}

export const layoutsLead = (w: AssessWords) =>
  w.hiring
    ? "Optional. A layout is the set of sections every new station starts with, so all your stations read the same way."
    : "Define layout and fields for clinical stations. Saved drafts and published versions appear below, but not the starting layouts on the new-template wizard.";

export const newLayoutLabel = (w: AssessWords) => (w.hiring ? "New layout" : "Create station template");

export const layoutKindLabel = (examCode: string | null, copiedFromId: string | null | undefined, w: AssessWords) =>
  [examCode, w.hiring && copiedFromId ? "copied from OSCE Guide standard" : ""].filter(Boolean).join(" · ");

/** The exam wizard's marking-scheme choices: an employer starts from ours or blank. */
export const schemeWayTitle = (id: "use" | "copy" | "write", fallback: string, w: AssessWords) =>
  w.hiring ? ({ use: fallback, copy: "Start from ours", write: "Start blank" })[id] : fallback;

export const formalToneLabel = (w: AssessWords) => `Formal ${w.examiner}`;

export const examinerLayoutTitle = (w: AssessWords) => `${w.Examiner} layout`;

export const programmeDialogLead = (w: AssessWords) =>
  `Choose the exam. ${w.Sittings} you schedule for it are grouped under this programme.`;

export const examDateFieldLabel = (w: AssessWords) => `Exam date wording (shown to ${w.trainees})`;

export const examinerTipsLabel = (w: AssessWords) => `Show ${w.examiner} tips while marking`;

export const examSettingsSubtitle = (w: AssessWords) =>
  `Every setting an exam has: its timings, how it is marked, and what ${w.trainees} get after a station.`;

export const stationExamHint = (w: AssessWords) =>
  `Only exams that are ready show here. A station can only go into ${w.sittings} of its own exam.`;

export const examConfirmMessage = (kind: "retire" | "delete", w: AssessWords) =>
  kind === "retire"
    ? w.hiring
      ? `It stops being offered for new practice and ${w.sittings}, and cannot be published again. Past attempts and results are kept.`
      : "It stops being offered for new practice and sittings, and cannot be published again. What was already attempted against it stays as it is."
    : `Only a draft nothing was ever built on can be deleted this way. Anything with a station, ${w.hiring ? "an" : "a"} ${w.sitting} or an attempt against it cannot be deleted. Retire it instead.`;

export const examDeleteBlocked = (w: AssessWords) =>
  `Can't delete: this exam has ${w.sittings} and recordings. Retire it instead, and its records stay.`;

export const newExamNameLead = (w: AssessWords) =>
  `This is what ${w.supervisors} and ${w.trainees} will see on every ${w.sitting}.`;

export const newExamTimingsLead = (w: AssessWords) =>
  `These are the defaults for every ${w.circuit}. You can change them per ${w.circuit} when you schedule.`;

export const usedByText = (count: number, w: AssessWords) =>
  `Used ${count} time${count === 1 ? "" : "s"}: by ${w.circuits}, attempts, peer sessions and practice sets`;

export const markedLiveLabel = (w: AssessWords) =>
  w.hiring ? `Can be marked live during the station (by an ${w.supervisor})` : "Can be judged while the station is running";

export const archiveVersionMessage = (version: number | string, w: AssessWords) =>
  `Version ${version} stops being used to mark new attempts. If it is the current version, the newest other published version takes over. It is refused while an exam or an upcoming ${w.sitting} still uses it.`;

export const publishVersionLead = (w: AssessWords) =>
  `Once published it cannot be changed. ${w.Sittings} already marked keep the version they used.`;

export const schemeSubtitle = (version: number | string, owned: boolean, w: AssessWords) =>
  `Exams › Marking schemes · version ${version}${owned ? "" : " · OSCE Guide catalogue"}. How a station is marked, and what the candidate's feedback looks like. Publishing makes a new version; ${w.sittings} already marked keep the version they used.`;

export const markingInstructionsHelp = (w: AssessWords) =>
  w.hiring ? `Used by the AI marker and shown to ${w.supervisors}.` : "Written for the AI marker and for supervisors.";

export const livePromptsHelp = (w: AssessWords) =>
  w.hiring
    ? `The seconds at which the live prompts to the ${w.supervisor} change to the next stage. Leave blank to have no timed prompts.`
    : "When the live supervisor prompts move on. Leave blank for none.";

export const reviewLayoutHelp = (w: AssessWords) => `What the ${w.supervisor} sees when reviewing a station, in order.`;

export const fieldTypesHelp = (w: AssessWords) =>
  `Pick the type that best matches what you want ${w.trainees} or ${w.examiners} to fill in.`;

export const stationLayoutNext = (w: AssessWords) =>
  `Pick a layout, then write the station in the builder: patient, ${w.examiner}, marking, photos, preview and versions.`;

export const briefLabel = (w: AssessWords) => (w.hiring ? "Candidate brief" : "Reading brief");

/** Why Publish is off, under the button; null when it is allowed. A hire station cannot go out with no candidate brief. */
export function publishBlockReason(noBrief: boolean, w: AssessWords): string | null {
  return w.hiring && noBrief ? "Publish needs a candidate brief." : null;
}

export const noBriefWarning = (w: AssessWords) =>
  `This station has no candidate brief, so candidates see nothing during reading time.${w.hiring ? "" : " You can still publish."}`;

const NAME_TAKEN = "You already have an exam with that name. Pick another name, or open the one you have.";

/**
 * The plain-words refusal for an exam save, or null to keep the server's message. A taken name reads
 * the same for both arms; "in use" is spelled out only for hire, whose employers see no circuit board.
 */
export function examRefusalMessage(code: string | null | undefined, w: AssessWords): string | null {
  if (code === "exam_code_taken" || code === "programme_exists") return NAME_TAKEN;
  if (code === "exam_in_use" && w.hiring) return "This exam is in use. An assessment uses it. Cancel or finish that assessment first.";
  return null;
}

/** The employer's way to adopt an exam we already built: the card on New exam, and the sentence under an empty station list. Null where the institution workspace keeps its own wording. */
export const startFromOurs = (w: AssessWords) =>
  w.hiring ? { title: "Start from ours", body: "Stations and marking already written. You can change anything after." } : null;

export const stationsEmptyBody = (canAuthor: boolean, readerText: string, w: AssessWords) =>
  canAuthor
    ? w.hiring
      ? "Write one, import one you already use, or start from an exam of ours."
      : "Create one with New station, from a template or straight from a prompt."
    : readerText;

export const startFromOursLabel = (w: AssessWords) => (w.hiring ? "Start from an exam of ours" : null);
