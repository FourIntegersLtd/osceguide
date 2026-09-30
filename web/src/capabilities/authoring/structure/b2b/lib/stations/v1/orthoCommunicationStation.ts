import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { withStationGeneration } from "@/capabilities/authoring/structure/b2b/lib/stations/generationProfileKeys";

/** Ortho communication — version 1, B2C admin section groups. */
export function orthoCommunicationStationTemplateV1(): StationStructure {
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
        ],
      },
      {
        id: "communication_themes",
        title: "Communication Themes",
        audience: "examiner",
        blocks: [
          {
            id: "communication_themes",
            type: "list",
            role: "examiner",
            label: "Communication Themes",
          },
          {
            id: "professional_conduct_topics",
            type: "list",
            role: "examiner",
            label: "Professional Conduct Topics",
          },
        ],
      },
      {
        id: "communication_frameworks",
        title: "Communication Frameworks",
        audience: "examiner",
        blocks: [
          {
            id: "consent_approach",
            type: "longText",
            role: "examiner",
            label: "Consent Approach",
          },
          {
            id: "breaking_bad_news_framework",
            type: "longText",
            role: "examiner",
            label: "Breaking Bad News Framework",
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
    "ortho.communication",
  );
}
