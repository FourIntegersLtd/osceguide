import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { withStationGeneration } from "@/capabilities/authoring/structure/b2b/lib/stations/generationProfileKeys";

/** Ortho clinical station — version 1 (OrthoClinicalStationModel), B2C admin section groups. */
export function orthoClinicalStationTemplateV1(): StationStructure {
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
            id: "radiograph_image_url",
            type: "shortText",
            role: "candidate_brief",
            label: "Radiograph Image URL",
            placeholder: "Optional URL to primary imaging",
          },
        ],
      },
      {
        id: "key_concerns",
        title: "Key Concerns",
        audience: "examiner",
        blocks: [
          {
            id: "key_concerns",
            type: "list",
            role: "examiner",
            label: "Key Concerns",
          },
        ],
      },
      {
        id: "clinical_assessment",
        title: "Clinical Assessment",
        audience: "examiner",
        blocks: [
          {
            id: "history_overview",
            type: "longText",
            role: "examiner",
            label: "History Overview",
          },
          {
            id: "examination_overview",
            type: "longText",
            role: "examiner",
            label: "Examination Overview",
          },
          {
            id: "investigations_overview",
            type: "longText",
            role: "examiner",
            label: "Investigations Overview",
          },
          {
            id: "management_overview",
            type: "longText",
            role: "examiner",
            label: "Management Overview",
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
            type: "longText",
            role: "examiner",
            label: "Interview Questions",
            placeholder: "Question and answer pairs for the examiner",
          },
        ],
      },
      {
        id: "references",
        title: "References",
        audience: "examiner",
        blocks: [
          {
            id: "references",
            type: "list",
            role: "examiner",
            label: "References",
          },
        ],
      },
    ],
  },
    "ortho.clinical",
  );
}
