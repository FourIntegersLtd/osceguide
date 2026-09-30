import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { withStationGeneration } from "@/capabilities/authoring/structure/b2b/lib/stations/generationProfileKeys";
import { consultationStructure } from "@/capabilities/authoring/structure/b2b/lib/stations/stationPatientScript";
import {
  b2cDoctorInformationSection,
  b2cManagementPlanSection,
  b2cPatientInformationSection,
} from "@/capabilities/authoring/structure/b2b/lib/stations/b2cStationSections";

/** CASC station template — version 1 (CascStationModel), B2C admin section groups. */
export function cascStationTemplateV1(): StationStructure {
  return withStationGeneration(
    consultationStructure([
    b2cPatientInformationSection(),
    b2cDoctorInformationSection([
      {
        id: "doctor_task",
        type: "longText",
        role: "candidate_brief",
        label: "Doctor Task",
        required: true,
      },
    ]),
    b2cManagementPlanSection([
      {
        id: "description",
        type: "longText",
        role: "examiner",
        label: "Description",
      },
      {
        id: "diagnostic_criteria",
        type: "list",
        role: "examiner",
        label: "Diagnostic Criteria",
      },
      {
        id: "differential_diagnosis",
        type: "list",
        role: "examiner",
        label: "Differential Diagnosis",
      },
      {
        id: "explanation",
        type: "longText",
        role: "examiner",
        label: "Explanation",
      },
      {
        id: "assessment",
        type: "list",
        role: "examiner",
        label: "Assessment",
      },
      {
        id: "risk_factors",
        type: "list",
        role: "examiner",
        label: "Risk Factors",
      },
      {
        id: "immediate_actions",
        type: "list",
        role: "examiner",
        label: "Immediate Actions",
      },
      {
        id: "pharmacological_treatment",
        type: "list",
        role: "examiner",
        label: "Pharmacological Treatment",
      },
      {
        id: "psychological_treatment",
        type: "list",
        role: "examiner",
        label: "Psychological Treatment",
      },
      {
        id: "social_interventions",
        type: "list",
        role: "examiner",
        label: "Social Interventions",
      },
      {
        id: "safety_planning",
        type: "list",
        role: "examiner",
        label: "Safety Planning",
      },
      {
        id: "follow_up",
        type: "list",
        role: "examiner",
        label: "Follow Up",
      },
      {
        id: "additional_notes",
        type: "longText",
        role: "examiner",
        label: "Additional Notes",
      },
    ]),
  ]),
    "casc.station",
  );
}
