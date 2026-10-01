import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { orthoCompetencyBlocks } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/blocks";

/** Ortho feedback template — version 1 (OrthoFeedbackModel + platform rubric ids). */
export function orthoFeedbackTemplateV1(): StationStructure {
  return {
    schemaVersion: 1,
    sections: [
      {
        id: "sec_clinical_skills",
        title: "Clinical skills",
        description: "Use for clinical station types; leave empty for other types.",
        blocks: [
          ...orthoCompetencyBlocks(
            "clinical_skills",
            "clinical_skills_technical_knowledge_clinical_expertise",
            "Technical knowledge & clinical expertise",
          ),
          ...orthoCompetencyBlocks(
            "clinical_skills",
            "clinical_skills_situational_awareness",
            "Situational awareness",
          ),
          ...orthoCompetencyBlocks(
            "clinical_skills",
            "clinical_skills_communication_information_gathering",
            "Communication: information gathering",
          ),
          ...orthoCompetencyBlocks(
            "clinical_skills",
            "clinical_skills_problem_solving_decision_making",
            "Problem solving & decision making",
          ),
          ...orthoCompetencyBlocks(
            "clinical_skills",
            "clinical_skills_communication_information_giving",
            "Communication: information giving",
          ),
        ],
      },
      {
        id: "sec_prioritisation_skills",
        title: "Prioritisation skills",
        description: "Use for prioritisation station types.",
        blocks: [
          ...orthoCompetencyBlocks(
            "prioritisation_skills",
            "organisation_planning",
            "Organisation & planning",
          ),
          ...orthoCompetencyBlocks(
            "prioritisation_skills",
            "prioritisation_skills_judgement_under_pressure",
            "Judgement under pressure",
          ),
          ...orthoCompetencyBlocks(
            "prioritisation_skills",
            "prioritisation_skills_situational_awareness",
            "Situational awareness",
          ),
          ...orthoCompetencyBlocks(
            "prioritisation_skills",
            "prioritisation_skills_problem_solving_decision_making",
            "Problem solving & decision making",
          ),
          ...orthoCompetencyBlocks(
            "prioritisation_skills",
            "prioritisation_skills_communication_information_gathering",
            "Communication: information gathering",
          ),
        ],
      },
      {
        id: "sec_communication_skills",
        title: "Communication skills",
        description: "Use for communication station types.",
        blocks: [
          ...orthoCompetencyBlocks(
            "communication_skills",
            "communication_skills_communication_information_gathering",
            "Communication: information gathering",
          ),
          ...orthoCompetencyBlocks(
            "communication_skills",
            "communication_skills_communication_information_giving",
            "Communication: information giving",
          ),
          ...orthoCompetencyBlocks(
            "communication_skills",
            "communication_skills_situational_awareness",
            "Situational awareness",
          ),
          ...orthoCompetencyBlocks(
            "communication_skills",
            "communication_skills_judgement_under_pressure",
            "Judgement under pressure",
          ),
          ...orthoCompetencyBlocks(
            "communication_skills",
            "communication_skills_technical_knowledge_clinical_expertise",
            "Technical knowledge & clinical expertise",
          ),
        ],
      },
      {
        id: "sec_portfolio_skills",
        title: "Portfolio skills",
        description: "Use for portfolio station types.",
        blocks: [
          ...orthoCompetencyBlocks(
            "portfolio_skills",
            "person_specifications_cv_articulation",
            "Person specifications & CV articulation",
          ),
          ...orthoCompetencyBlocks(
            "portfolio_skills",
            "portfolio_knowledge",
            "Portfolio knowledge",
          ),
          ...orthoCompetencyBlocks(
            "portfolio_skills",
            "reflection_professional_conduct",
            "Reflection & professional conduct",
          ),
          ...orthoCompetencyBlocks(
            "portfolio_skills",
            "portfolio_skills_communication_information_giving",
            "Communication: information giving",
          ),
          ...orthoCompetencyBlocks(
            "portfolio_skills",
            "critical_thinking_justification",
            "Critical thinking & justification",
          ),
        ],
      },
    ],
  };
}
