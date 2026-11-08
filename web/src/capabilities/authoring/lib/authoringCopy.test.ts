import assert from "node:assert/strict";
import test from "node:test";
import { assessWordsFor } from "@/capabilities/assess-words/vocabulary";
import * as copy from "@/capabilities/authoring/lib/authoringCopy";
import { examNextAction, toggleHelp } from "@/capabilities/authoring/sections/examSteps";

const hire = assessWordsFor("hire");
const inst = assessWordsFor("assess");

test("exams list: hire says Available and empty copy points at the fix in employer words", () => {
  assert.equal(copy.examChipLabel("Ready to schedule", hire), "Available");
  assert.equal(copy.examChipLabel("Draft", hire), "Draft");
  assert.equal(copy.examChipLabel("Ready to schedule", inst), "Ready to schedule");
  assert.equal(copy.examEmptyBody(hire), "Start from one of ours, or build your own. You need one before you can schedule an assessment.");
  assert.equal(copy.examEmptyBody(inst), "Create an exam, attach a marking scheme version, then publish it to run sittings against it.");
});

test("exam page: toggle help, next line, retire and delete read in the workspace's words", () => {
  assert.equal(toggleHelp(true, hire), "On: this exam can be picked when you schedule an assessment.");
  assert.equal(toggleHelp(false, hire), "Off: existing assessments carry on, but no new ones can be scheduled.");
  assert.equal(toggleHelp(true), "On: this exam can be picked when you schedule a sitting.");
  assert.equal(examNextAction({ status: "retired" }, hire).line, "Retired. It is no longer offered for new assessments.");
  assert.equal(examNextAction({ status: "retired" }).line, "Retired. It is no longer offered for new sittings.");
  assert.equal(copy.examConfirmMessage("retire", inst), "It stops being offered for new practice and sittings, and cannot be published again. What was already attempted against it stays as it is.");
  assert.equal(copy.examConfirmMessage("retire", hire), "It stops being offered for new practice and assessments, and cannot be published again. Past attempts and results are kept.");
  assert.equal(copy.examConfirmMessage("delete", inst), "Only a draft nothing was ever built on can be deleted this way. Anything with a station, a sitting or an attempt against it cannot be deleted. Retire it instead.");
  assert.equal(copy.examConfirmMessage("delete", hire), "Only a draft nothing was ever built on can be deleted this way. Anything with a station, an assessment or an attempt against it cannot be deleted. Retire it instead.");
  assert.equal(copy.examDeleteBlocked(hire), "Can't delete: this exam has assessments and recordings. Retire it instead, and its records stay.");
  assert.equal(hire.scheduleSitting, "Schedule an assessment");
  assert.equal(inst.scheduleSitting, "Schedule a sitting");
});

test("new exam, settings and programmes copy", () => {
  assert.equal(copy.newExamNameLead(hire), "This is what assessors and candidates will see on every assessment.");
  assert.equal(copy.newExamNameLead(inst), "This is what supervisors and trainees will see on every sitting.");
  assert.equal(copy.newExamTimingsLead(hire), "These are the defaults for every rotation. You can change them per rotation when you schedule.");
  assert.equal(copy.examDateFieldLabel(hire), "Exam date wording (shown to candidates)");
  assert.equal(copy.examDateFieldLabel(inst), "Exam date wording (shown to trainees)");
  assert.equal(copy.examinerTipsLabel(hire), "Show assessor tips while marking");
  assert.equal(copy.examinerTipsLabel(inst), "Show examiner tips while marking");
  assert.equal(copy.examSettingsSubtitle(hire), "Every setting an exam has: its timings, how it is marked, and what candidates get after a station.");
  assert.equal(copy.programmeLead(hire), "A programme groups this organisation's assessments under one exam.");
  assert.equal(copy.programmeLead(inst), "A programme groups this institution's sittings under one exam.");
  assert.equal(copy.programmeDialogLead(hire), "Choose the exam. Assessments you schedule for it are grouped under this programme.");
  assert.equal(copy.programmeEmptyBody(inst), "Add a programme for each exam you run sittings against.");
});

test("stations: exam hint, layout step and used-by line", () => {
  assert.equal(copy.stationExamHint(hire), "Only exams that are ready show here. A station can only go into assessments of its own exam.");
  assert.equal(copy.stationLayoutNext(hire), "Pick a layout, then write the station in the builder: patient, assessor, marking, photos, preview and versions.");
  assert.equal(copy.stationLayoutNext(inst), "Pick a layout, then write the station in the builder: patient, examiner, marking, photos, preview and versions.");
  assert.equal(copy.usedByText(2, hire), "Used 2 times: by rotations, attempts, peer sessions and practice sets");
  assert.equal(copy.usedByText(1, inst), "Used 1 time: by circuits, attempts, peer sessions and practice sets");
});

test("station builder: hire says Candidate brief and blocks Publish with its reason; an institution keeps Reading brief and may publish", () => {
  assert.equal(copy.briefLabel(hire), "Candidate brief");
  assert.equal(copy.briefLabel(inst), "Reading brief");
  assert.equal(copy.publishBlockReason(true, hire), "Publish needs a candidate brief.");
  assert.equal(copy.publishBlockReason(false, hire), null);
  assert.equal(copy.publishBlockReason(true, inst), null);
  assert.equal(copy.noBriefWarning(inst), "This station has no candidate brief, so candidates see nothing during reading time. You can still publish.");
  assert.equal(copy.noBriefWarning(hire), "This station has no candidate brief, so candidates see nothing during reading time.");
});

test("marking scheme copy (words only): live marking, versions and advanced help", () => {
  assert.equal(copy.markedLiveLabel(hire), "Can be marked live during the station (by an assessor)");
  assert.equal(copy.markedLiveLabel(inst), "Can be judged while the station is running");
  assert.equal(copy.publishVersionLead(hire), "Once published it cannot be changed. Assessments already marked keep the version they used.");
  assert.equal(copy.publishVersionLead(inst), "Once published it cannot be changed. Sittings already marked keep the version they used.");
  assert.equal(copy.archiveVersionMessage(3, hire), "Version 3 stops being used to mark new attempts. If it is the current version, the newest other published version takes over. It is refused while an exam or an upcoming assessment still uses it.");
  assert.equal(copy.schemeSubtitle(4, true, hire), "Exams › Marking schemes · version 4. How a station is marked, and what the candidate's feedback looks like. Publishing makes a new version; assessments already marked keep the version they used.");
  assert.equal(copy.markingInstructionsHelp(inst), "Written for the AI marker and for supervisors.");
  assert.equal(copy.livePromptsHelp(inst), "When the live supervisor prompts move on. Leave blank for none.");
  assert.equal(copy.markingInstructionsHelp(hire), "Used by the AI marker and shown to assessors.");
  assert.equal(copy.reviewLayoutHelp(inst), "What the supervisor sees when reviewing a station, in order.");
  assert.equal(copy.livePromptsHelp(hire), "The seconds at which the live prompts to the assessor change to the next stage. Leave blank to have no timed prompts.");
  assert.equal(copy.fieldTypesHelp(hire), "Pick the type that best matches what you want candidates or assessors to fill in.");
});

test("a taken exam name reads the same for both arms; exam_in_use is spelled out for hire only", () => {
  const taken = "You already have an exam with that name. Pick another name, or open the one you have.";
  for (const w of [hire, inst]) {
    assert.equal(copy.examRefusalMessage("exam_code_taken", w), taken);
    assert.equal(copy.examRefusalMessage("programme_exists", w), taken);
  }
  assert.equal(
    copy.examRefusalMessage("exam_in_use", hire),
    "This exam is in use. An assessment uses it. Cancel or finish that assessment first.",
  );
  assert.equal(copy.examRefusalMessage("exam_in_use", inst), null);
  assert.equal(copy.examRefusalMessage("other", hire), null);
});

test("hire board copy: exams, stations, builder and layouts in employer words; institution unchanged", () => {
  assert.equal(copy.programmeEmptyTitle(hire), "No exams offered yet");
  assert.equal(copy.programmeEmptyTitle(inst), "No programmes yet");
  assert.equal(copy.authoringLead(hire), "What you assess candidates on: the stations and how they are marked.");
  assert.match(copy.authoringLead(inst), /^Everything you examine with:/);
  assert.equal(copy.stationsLead(hire), "The scenarios candidates work through. Each has a patient, a brief and the marking it uses.");
  assert.equal(copy.stationsLead(inst), "Published station cases for sessions and practice.");
  assert.equal(copy.importLabel(hire), "Import a document");
  assert.equal(copy.importLabel(inst), "Import from PDF or Word");
  assert.equal(copy.stationBuilderLead(hire), "Write the brief, the patient and the assessor's notes. Publish when it reads right.");
  assert.equal(copy.stationBuilderLead(inst), null);
  assert.equal(copy.briefHelp(hire), "The candidate sees this in their assessment page before the station starts.");
  assert.equal(copy.briefHelp(inst), "What the candidate reads before the station starts. Saving this does not cut a new version.");
  assert.equal(copy.addPhotoLabel(hire), "Add a photo");
  assert.equal(copy.addPhotoLabel(inst), "Add");
  assert.equal(copy.generateDraftHeading(hire), "What is it about?");
  assert.equal(copy.generateDraftHelp(hire), "We write a first draft you then edit. Nothing is published until you press Publish.");
  assert.equal(copy.generateDraftHeading(inst), "Generate draft");
  assert.deepEqual(copy.examinerSectionNote("Examiner notes", hire), { title: "Assessor's notes", help: "Assessors see these on the marking page. Candidates never do." });
  assert.equal(copy.examinerSectionNote("Examiner notes", inst), null);
  assert.equal(copy.layoutsLead(hire), "Optional. A layout is the set of sections every new station starts with, so all your stations read the same way.");
  assert.equal(copy.newLayoutLabel(hire), "New layout");
  assert.equal(copy.newLayoutLabel(inst), "Create station template");
  assert.equal(copy.layoutKindLabel("ACME", "t1", hire), "ACME · copied from OSCE Guide standard");
  assert.equal(copy.layoutKindLabel("ACME", null, hire), "ACME");
  assert.equal(copy.layoutKindLabel("ACME", "t1", inst), "ACME");
  assert.equal(copy.schemeWayTitle("copy", "Copy one from OSCE Guide", hire), "Start from ours");
  assert.equal(copy.schemeWayTitle("write", "Write a new marking scheme", hire), "Start blank");
  assert.equal(copy.schemeWayTitle("copy", "Copy one from OSCE Guide", inst), "Copy one from OSCE Guide");
  assert.equal(copy.formalToneLabel(hire), "Formal assessor");
  assert.equal(copy.formalToneLabel(inst), "Formal examiner");
  assert.equal(copy.examinerLayoutTitle(hire), "Assessor layout");
  assert.equal(copy.examinerLayoutTitle(inst), "Examiner layout");
});

test("start from ours: employer words on New exam and the empty station list, institution text unchanged", () => {
  assert.deepEqual(copy.startFromOurs(hire), { title: "Start from ours", body: "Stations and marking already written. You can change anything after." });
  assert.equal(copy.startFromOurs(inst), null);
  assert.equal(copy.startFromOursLabel(hire), "Start from an exam of ours");
  assert.equal(copy.startFromOursLabel(inst), null);
  assert.equal(copy.stationsEmptyBody(true, "R", hire), "Write one, import one you already use, or start from an exam of ours.");
  assert.equal(copy.stationsEmptyBody(true, "R", inst), "Create one with New station, from a template or straight from a prompt.");
  assert.equal(copy.stationsEmptyBody(false, "R", hire), "R");
});
