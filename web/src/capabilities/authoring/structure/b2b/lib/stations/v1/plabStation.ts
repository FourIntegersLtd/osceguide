import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { withStationGeneration } from "@/capabilities/authoring/structure/b2b/lib/stations/generationProfileKeys";
import { consultationStructure } from "@/capabilities/authoring/structure/b2b/lib/stations/stationPatientScript";
import {
  b2cDoctorInformationSection,
  b2cManagementPlanSection,
  b2cPatientInformationSection,
} from "@/capabilities/authoring/structure/b2b/lib/stations/b2cStationSections";

/** PLAB 2 station template — version 1 (PlabStationModel), B2C admin section groups. */
export function plabStationTemplateV1(): StationStructure {
  return withStationGeneration(
    consultationStructure([
    b2cPatientInformationSection([
      {
        id: "examination_findings",
        type: "list",
        role: "examination",
        label: "Examination findings",
      },
    ]),
    b2cDoctorInformationSection([
      {
        id: "doctor_identity",
        type: "longText",
        role: "candidate_brief",
        label: "Doctor Identity",
        required: true,
        placeholder: "e.g. You are an FY2 in the emergency department.",
      },
      {
        id: "patient_information",
        type: "list",
        role: "candidate_brief",
        label: "Patient Information",
      },
      {
        id: "task_instructions",
        type: "longText",
        role: "candidate_brief",
        label: "Task Instructions",
        required: true,
      },
    ]),
    b2cManagementPlanSection([
      {
        id: "explanation",
        type: "longText",
        role: "examiner",
        label: "Explanation",
      },
      {
        id: "differential_diagnosis",
        type: "list",
        role: "examiner",
        label: "Differential Diagnosis",
      },
      {
        id: "assessment",
        type: "list",
        role: "examiner",
        label: "Clinical Assessment",
      },
      {
        id: "management_examination_findings",
        type: "list",
        role: "examiner",
        label: "Clinical Examination Findings",
      },
      {
        id: "further_investigations",
        type: "list",
        role: "examiner",
        label: "Further Investigations",
      },
      {
        id: "pharmacological_treatment",
        type: "list",
        role: "examiner",
        label: "Pharmacological Management",
      },
      {
        id: "non_pharmacological_treatment",
        type: "list",
        role: "examiner",
        label: "Non-Pharmacological Management",
      },
      {
        id: "health_education",
        type: "list",
        role: "examiner",
        label: "Health Education",
      },
      {
        id: "follow_up",
        type: "longText",
        role: "examiner",
        label: "Follow Up",
      },
      {
        id: "safety_netting",
        type: "longText",
        role: "examiner",
        label: "Safety Netting",
      },
      {
        id: "social_concerns",
        type: "list",
        role: "examiner",
        label: "Social Concerns",
      },
      {
        id: "ice",
        type: "list",
        role: "examiner",
        label: "ICE",
      },
      {
        id: "additional_notes",
        type: "longText",
        role: "examiner",
        label: "Additional Notes",
      },
      {
        id: "specialties",
        type: "list",
        role: "examiner",
        label: "Specialties",
        placeholder: "Lowercase, e.g. cardiology",
      },
    ]),
  ]),
    "plab.station",
  );
}
