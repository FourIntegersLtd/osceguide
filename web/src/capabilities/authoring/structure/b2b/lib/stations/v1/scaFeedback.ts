import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { ragBlock } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/blocks";

/** RCGP SCA feedback template — version 1 (FeedbackModel). */
export function scaFeedbackTemplateV1(): StationStructure {
  return {
    schemaVersion: 1,
    sections: [
      {
        id: "sec_global_skills",
        title: "Global skills",
        blocks: [
          ragBlock("global_skills.structures_consultation", "Structures consultation"),
          ragBlock("global_skills.avoids_repetition", "Avoids repetition"),
          ragBlock("global_skills.progresses_through_tasks", "Progresses through tasks"),
          ragBlock(
            "global_skills.recognises_ethical_implications",
            "Recognises ethical implications",
          ),
          ragBlock("global_skills.finishes_data_gathering", "Finishes data gathering"),
          ragBlock("global_skills.uses_clear_language", "Uses clear language"),
          ragBlock(
            "global_skills.remains_responsive_to_patient",
            "Remains responsive to patient",
          ),
        ],
      },
      {
        id: "sec_tasks",
        title: "Tasks",
        blocks: [
          ragBlock("tasks.opens_consultation", "Opens consultation"),
          ragBlock("tasks.discovers_psychosocial_context", "Discovers psychosocial context"),
          ragBlock("tasks.identifies_cues", "Identifies cues"),
          ragBlock("tasks.discovers_ice", "Discovers ICE"),
          ragBlock("tasks.interprets_tests", "Interprets tests"),
          ragBlock("tasks.generates_hypotheses", "Generates hypotheses"),
          ragBlock("tasks.rules_in_out_disease", "Rules in/out disease"),
          ragBlock("tasks.reaches_diagnosis", "Reaches diagnosis"),
          ragBlock("tasks.offers_management_plan", "Offers management plan"),
          ragBlock("tasks.manages_comorbidity", "Manages comorbidity"),
          ragBlock("tasks.provides_safety_net", "Provides safety net"),
        ],
      },
      {
        id: "sec_relating",
        title: "Relating to others",
        blocks: [
          ragBlock("relating_to_others.clarifies_cues", "Clarifies cues"),
          ragBlock("relating_to_others.listens_curiosity", "Listens with curiosity"),
          ragBlock("relating_to_others.generates_rapport", "Generates rapport"),
          ragBlock("relating_to_others.uses_open_questions", "Uses open questions"),
          ragBlock("relating_to_others.uses_closed_questions", "Uses closed questions"),
          ragBlock("relating_to_others.explains_rationale", "Explains rationale"),
          ragBlock("relating_to_others.verbalises_diagnosis", "Verbalises diagnosis"),
          ragBlock("relating_to_others.shares_ice_plan", "Shares ICE plan"),
          ragBlock(
            "relating_to_others.negotiates_psychosocial_plan",
            "Negotiates psychosocial plan",
          ),
          ragBlock("relating_to_others.shares_risks", "Shares risks"),
          ragBlock(
            "relating_to_others.supports_decision_making",
            "Supports decision making",
          ),
        ],
      },
      {
        id: "sec_clinical_analysis",
        title: "Clinical analysis",
        blocks: [
          { id: "clinical_analysis_missed_history", type: "list", label: "Missed history" },
          { id: "clinical_analysis_key_positives", type: "list", label: "Key positives" },
          { id: "clinical_analysis_key_negatives", type: "list", label: "Key negatives" },
          {
            id: "clinical_analysis_missed_examinations",
            type: "list",
            label: "Missed examinations",
          },
          {
            id: "clinical_analysis_safety_considerations",
            type: "list",
            label: "Safety considerations",
          },
          {
            id: "clinical_analysis_psychosocial_impact",
            type: "list",
            label: "Psychosocial impact",
          },
          {
            id: "clinical_analysis_lifestyle_factors",
            type: "list",
            label: "Lifestyle factors",
          },
        ],
      },
      {
        id: "sec_actionable_feedback",
        title: "Priorities",
        blocks: [
          {
            id: "actionable_feedback_overall_priorities",
            type: "list",
            label: "Overall priorities",
            placeholder: "Area, current level, steps, expected outcome",
          },
        ],
      },
    ],
  };
}
