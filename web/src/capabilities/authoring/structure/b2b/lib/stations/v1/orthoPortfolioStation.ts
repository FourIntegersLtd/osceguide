import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { withStationGeneration } from "@/capabilities/authoring/structure/b2b/lib/stations/generationProfileKeys";

/** Ortho portfolio — version 1, B2C admin section groups. */
export function orthoPortfolioStationTemplateV1(): StationStructure {
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
            id: "clinical_scenario",
            type: "longText",
            role: "candidate_brief",
            label: "Clinical Scenario",
            required: true,
          },
          {
            id: "duration_minutes",
            type: "shortText",
            role: "candidate_brief",
            label: "Duration (minutes)",
          },
          {
            id: "portfolio_themes",
            type: "list",
            role: "candidate_brief",
            label: "Portfolio Themes",
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
          },
        ],
      },
      {
        id: "key_learning_points",
        title: "Key Learning Points",
        audience: "examiner",
        blocks: [
          {
            id: "key_learning_points",
            type: "list",
            role: "examiner",
            label: "Key Learning Points",
          },
        ],
      },
    ],
  },
    "ortho.portfolio",
  );
}
