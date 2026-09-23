import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import {
  consultationStructure,
  patientScriptSections,
} from "@/capabilities/authoring/structure/b2b/lib/stations/stationPatientScript";

/** Abnormal-results call: patient script, the results and record the candidate sees, and the examiner's plan. */
export function asterixPresetStructure(): StationStructure {
  return consultationStructure([
    ...patientScriptSections(),
    {
      id: "sec_candidate_results",
      title: "Results to discuss",
      audience: "candidate",
      description: "Recent abnormal results first. Blood results, imaging, or both.",
      blocks: [
      {
        id: "doctor_patient_biodata",
        type: "shortText",
        role: "candidate_brief",
        label: "Basic identifiers",
      },
      {
        id: "investigation_type",
        type: "singleSelect",
        role: "candidate_brief",
        label: "Investigation type",
        options: ["Blood results", "Imaging", "Blood and imaging"],
      },
      {
        id: "recent_abnormal_results",
        type: "list",
        role: "candidate_brief",
        label: "Recent abnormal results",
        placeholder:
          "e.g. HbA1c 52 mmol/mol, chest X-ray showing left lower lobe opacity…",
      },
      {
        id: "past_results_trend",
        type: "list",
        role: "candidate_brief",
        label: "Past results and trend",
      },
      ],
    },
    {
      id: "sec_candidate_record",
      title: "Background from the notes",
      audience: "candidate",
      description: "What the doctor already knows about this patient.",
      blocks: [
      {
        id: "current_medications",
        type: "list",
        role: "candidate_brief",
        label: "Current medications",
      },
      {
        id: "past_medical_history",
        type: "list",
        role: "candidate_brief",
        label: "Past medical history",
      },
      {
        id: "social_history",
        type: "list",
        role: "candidate_brief",
        label: "Social history",
      },
      {
        id: "recent_notes",
        type: "list",
        role: "candidate_brief",
        label: "Recent notes",
      },
      ],
    },
    {
      id: "sec_examiner_assessment",
      title: "Assessment and explanation",
      audience: "examiner",
      description: "What to establish and how to explain the results.",
      blocks: [
      {
        id: "assessment",
        type: "list",
        role: "examiner",
        label: "Assessment prompts",
        placeholder:
          "e.g. What does the patient already know? Any red flags or symptoms?",
      },
      {
        id: "explanation",
        type: "longText",
        role: "examiner",
        label: "Explanation to the patient",
      },
      ],
    },
    {
      id: "sec_examiner_next",
      title: "Next steps",
      audience: "examiner",
      description: "Immediate actions and further work-up.",
      blocks: [
      {
        id: "immediate_actions",
        type: "list",
        role: "examiner",
        label: "Immediate actions",
      },
      {
        id: "further_investigations",
        type: "list",
        role: "examiner",
        label: "Further investigations",
      },
      ],
    },
    {
      id: "sec_examiner_followup",
      title: "Follow-up and safety",
      audience: "examiner",
      description: "Follow-up, education, safety netting and anything else.",
      blocks: [
      {
        id: "follow_up",
        type: "longText",
        role: "examiner",
        label: "Follow-up plan",
      },
      {
        id: "health_education",
        type: "list",
        role: "examiner",
        label: "Health education",
      },
      {
        id: "safety_netting",
        type: "longText",
        role: "examiner",
        label: "Safety netting",
      },
      {
        id: "additional_notes",
        type: "longText",
        role: "examiner",
        label: "Additional notes",
      },
      ],
    },
  ]);
}
