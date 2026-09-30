import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { plabCompetencyBlocks } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/blocks";

/** PLAB 2 feedback template — version 1 (PlabFeedbackModel). */
export function plabFeedbackTemplateV1(): StationStructure {
  return {
    schemaVersion: 1,
    sections: [
      {
        id: "sec_data_gathering",
        title: "Data gathering",
        blocks: [
          ...plabCompetencyBlocks("data_gathering", "history_taking", "History taking"),
          ...plabCompetencyBlocks("data_gathering", "examination", "Examination"),
          ...plabCompetencyBlocks("data_gathering", "investigations", "Investigations"),
          ...plabCompetencyBlocks("data_gathering", "interpretation", "Interpretation"),
        ],
      },
      {
        id: "sec_clinical_management",
        title: "Clinical management",
        blocks: [
          ...plabCompetencyBlocks("clinical_management", "diagnosis", "Diagnosis"),
          ...plabCompetencyBlocks(
            "clinical_management",
            "management_plan",
            "Management plan",
          ),
          ...plabCompetencyBlocks(
            "clinical_management",
            "safety_netting",
            "Safety netting",
          ),
          ...plabCompetencyBlocks("clinical_management", "follow_up", "Follow up"),
        ],
      },
      {
        id: "sec_interpersonal_skills",
        title: "Interpersonal skills",
        blocks: [
          ...plabCompetencyBlocks("interpersonal_skills", "language", "Language"),
          ...plabCompetencyBlocks("interpersonal_skills", "listening", "Listening"),
          ...plabCompetencyBlocks("interpersonal_skills", "rapport", "Rapport"),
          ...plabCompetencyBlocks("interpersonal_skills", "empathy", "Empathy"),
        ],
      },
    ],
  };
}
