import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { withStationGeneration } from "@/capabilities/authoring/structure/b2b/lib/stations/generationProfileKeys";
import { consultationStructure } from "@/capabilities/authoring/structure/b2b/lib/stations/stationPatientScript";
import {
  b2cDoctorInformationSection,
  b2cManagementPlanSection,
  b2cPatientInformationSection,
  scaClinicalExperienceSection,
} from "@/capabilities/authoring/structure/b2b/lib/stations/b2cStationSections";

/** RCGP SCA station template — version 1 (ScaStationModel), B2C admin section groups. */
export function scaStationTemplateV1(): StationStructure {
  return withStationGeneration(
    consultationStructure([
    b2cPatientInformationSection(),
    b2cDoctorInformationSection([
      {
        id: "doctor_patient_biodata",
        type: "longText",
        role: "candidate_brief",
        label: "Patient Biodata",
        placeholder: "e.g. John Doe, 35",
      },
      {
        id: "recent_notes",
        type: "list",
        role: "candidate_brief",
        label: "Recent Notes",
        placeholder:
          "Past GP visits only, not today's story. e.g. No recent GP visits; or Seen 2 months ago for medication review.",
      },
      {
        id: "current_medications",
        type: "list",
        role: "candidate_brief",
        label: "Current Medications",
      },
      {
        id: "past_medical_history",
        type: "list",
        role: "candidate_brief",
        label: "Past Medical History",
      },
      {
        id: "recent_investigations",
        type: "list",
        role: "candidate_brief",
        label: "Recent Investigations",
      },
      {
        id: "social_history",
        type: "list",
        role: "candidate_brief",
        label: "Social History",
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
        id: "assessment",
        type: "list",
        role: "examiner",
        label: "Assessment",
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
        id: "non_pharmacological_treatment",
        type: "list",
        role: "examiner",
        label: "Non-Pharmacological Treatment",
      },
      {
        id: "follow_up",
        type: "longText",
        role: "examiner",
        label: "Follow Up",
      },
      {
        id: "health_education",
        type: "list",
        role: "examiner",
        label: "Health Education",
      },
      {
        id: "safety_netting",
        type: "longText",
        role: "examiner",
        label: "Safety Netting",
      },
      {
        id: "additional_notes",
        type: "longText",
        role: "examiner",
        label: "Additional Notes",
      },
    ]),
    scaClinicalExperienceSection(),
  ]),
    "sca.station",
  );
}
