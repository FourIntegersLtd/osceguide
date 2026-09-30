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
  type Rubric,
  type RubricVersion,
  type Exam,
  type Programme,
} from "@/capabilities/authoring/api/scope";

export {
  listStations,
  STATION_PAGE_LIMIT,
  createStation,
  generateStation,
  autogenerateStationDraft,
  addStationVersion,
  editStationVersion,
  deleteStationVersion,
  archiveStationVersion,
  publishStationVersion,
  editStationBrief,
  uploadStationPhotos,
  removeStationPhoto,
  type StationPhotosResult,
} from "@/capabilities/authoring/api/stations";

export {
  listStationTemplates,
  listStationTemplatesPage,
  createStationTemplate,
  publishStationTemplate,
  addStationTemplateVersion,
  editStationTemplateVersion,
  deleteStationTemplateVersion,
  archiveStationTemplateVersion,
} from "@/capabilities/authoring/api/templates";

export {
  listRubrics,
  readRubric,
  addRubricVersion,
  editRubricVersion,
  renameRubric,
  archiveRubricVersion,
  publishRubricVersion,
  listRubricStartingPoints,
  previewRubric,
  copyRubric,
  draftRubricInstructions,
  trialMarkRubricVersion,
  listTrialCandidates,
  type RubricProblem,
  type RubricPreview,
  type RubricStartingPoint,
  type DraftInstruction,
  type TrialMark,
  type TrialMarkRequest,
  type TrialCandidate,
} from "@/capabilities/authoring/api/rubrics";

export {
  listExams,
  createExam,
  updateExam,
  publishExam,
  retireExam,
  deleteExam,
  listProgrammes,
  addProgramme,
  updateProgramme,
} from "@/capabilities/authoring/api/catalog";
