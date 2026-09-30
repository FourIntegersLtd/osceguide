import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { cascGenericDomainBlocks, competentBlock } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/blocks";

/** CASC feedback template — version 1 (CascFeedbackModel). */
export function cascFeedbackTemplateV1(): StationStructure {
  return {
    schemaVersion: 1,
    sections: [
      {
        id: "sec_history",
        title: "History",
        blocks: [
          competentBlock("history.identifies_priorities", "Identifies priorities"),
          competentBlock("history.recognizes_significance", "Recognizes significance"),
          competentBlock("history.explores_symptoms", "Explores symptoms"),
          competentBlock("history.assesses_risk", "Assesses risk"),
          competentBlock("history.explores_physical_health", "Explores physical health"),
          competentBlock("history.identifies_psychosocial", "Identifies psychosocial"),
          ...cascGenericDomainBlocks("history"),
        ],
      },
      {
        id: "sec_examination",
        title: "Examination",
        blocks: [
          competentBlock("examination.identifies_findings", "Identifies findings"),
          competentBlock("examination.recognizes_implications", "Recognizes implications"),
          competentBlock("examination.examination_competence", "Examination competence"),
          competentBlock("examination.formulates_diagnosis", "Formulates diagnosis"),
          ...cascGenericDomainBlocks("examination"),
        ],
      },
      {
        id: "sec_management",
        title: "Management",
        blocks: [
          competentBlock("management.problem_formulation", "Problem formulation"),
          competentBlock("management.management_plan", "Management plan"),
          competentBlock("management.risk_management", "Risk management"),
          competentBlock(
            "management.psychosocial_interventions",
            "Psychosocial interventions",
          ),
          ...cascGenericDomainBlocks("management"),
        ],
      },
      {
        id: "sec_communication",
        title: "Communication",
        blocks: [
          competentBlock("communication.consultation_structure", "Consultation structure"),
          competentBlock("communication.consultation_style", "Consultation style"),
          competentBlock("communication.professional_behavior", "Professional behavior"),
          competentBlock("communication.listening_skills", "Listening skills"),
          competentBlock("communication.questioning_technique", "Questioning technique"),
          competentBlock("communication.language_use", "Language use"),
          ...cascGenericDomainBlocks("communication"),
        ],
      },
    ],
  };
}
