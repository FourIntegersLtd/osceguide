import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { withStationGeneration } from "@/capabilities/authoring/structure/b2b/lib/stations/generationProfileKeys";

/** Ortho prioritisation — version 1, B2C admin section groups (flat blocks where nested in B2C). */
export function orthoPrioritisationStationTemplateV1(): StationStructure {
  return withStationGeneration(
    {
    schemaVersion: 1,
    layout: { persona: "examiner" },
    sections: [
      {
        id: "basic_information",
        title: "Basic Information",
        audience: "candidate",
        blocks: [
          {
            id: "clinical_scenario_title",
            type: "shortText",
            role: "candidate_brief",
            label: "Clinical Scenario Title",
            required: true,
          },
          {
            id: "clinical_scenario",
            type: "longText",
            role: "candidate_brief",
            label: "Clinical Scenario",
            required: true,
          },
          {
            id: "background_overview",
            type: "longText",
            role: "candidate_brief",
            label: "Background Overview",
          },
          {
            id: "suggested_order_overview",
            type: "longText",
            role: "examiner",
            label: "Suggested Order Overview",
          },
        ],
      },
      {
        id: "patient_lists",
        title: "Patient Lists",
        audience: "candidate",
        blocks: [
          {
            id: "patient_list_for_candidate",
            type: "records",
            fields: [
              { key: "number", label: "Patient" },
              { key: "age", label: "Age" },
              { key: "gender", label: "Gender" },
              { key: "summary", label: "Summary" },
              { key: "notes", label: "Notes" },
            ],
            role: "candidate_brief",
            label: "Patient List for Candidate",
          },
          {
            id: "examiner_additional_info",
            type: "records",
            fields: [
              { key: "number", label: "Patient" },
              { key: "age", label: "Age" },
              { key: "gender", label: "Gender" },
              { key: "summary", label: "Summary" },
              { key: "notes", label: "Notes" },
            ],
            role: "examiner",
            label: "Examiner Additional Info",
          },
        ],
      },
      {
        id: "suggested_list_order",
        title: "Suggested List Order",
        audience: "examiner",
        blocks: [
          {
            id: "suggested_order",
            type: "groupedList",
            role: "examiner",
            label: "Suggested List Order",
          },
        ],
      },
      {
        id: "interview_questions",
        title: "Interview Questions",
        audience: "examiner",
        blocks: [
          {
            id: "interview_questions",
            type: "qaList",
            role: "examiner",
            label: "Interview Questions",
          },
        ],
      },
    ],
  },
    "ortho.prioritisation",
  );
}
