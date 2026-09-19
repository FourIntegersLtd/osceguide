/*
 * The one place authoring talks to the backend.
 *
 * Split by section only so no file runs past 300 lines; the split that
 * matters is the one that is *not* here — there is no per-arm module, because
 * the scope is an argument. See `scope.ts`.
 */
export {
  authoringScope,
  supportsProgrammes,
  supportsBrief,
  supportsVersionDelete,
  pathId,
  type AuthoringScope,
  type Json,
  type Station,
  type StationVersion,
  type StationTemplate,
  type StationTemplateVersion,
  type FeedbackTemplate,
  type FeedbackTemplateVersion,
  type Rubric,
  type RubricVersion,
  type Exam,
  type Programme,
} from "@/capabilities/authoring/api/scope";

export {
  listStations,
  createStation,
  addStationVersion,
  editStationVersion,
  deleteStationVersion,
  archiveStationVersion,
  publishStationVersion,
  editStationBrief,
} from "@/capabilities/authoring/api/stations";

export {
  listStationTemplates,
  createStationTemplate,
  publishStationTemplate,
  addStationTemplateVersion,
  editStationTemplateVersion,
  listFeedbackTemplates,
  createFeedbackTemplate,
  publishFeedbackTemplate,
  addFeedbackTemplateVersion,
  editFeedbackTemplateVersion,
} from "@/capabilities/authoring/api/templates";

export {
  listRubrics,
  readRubric,
  createRubric,
  addRubricVersion,
  editRubricVersion,
  archiveRubricVersion,
  publishRubricVersion,
} from "@/capabilities/authoring/api/rubrics";

export {
  listExams,
  createExam,
  updateExam,
  publishExam,
  retireExam,
  listProgrammes,
  addProgramme,
  updateProgramme,
} from "@/capabilities/authoring/api/catalog";
