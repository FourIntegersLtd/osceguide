import type { StationBlock, StationSection } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { patientScriptSections } from "@/capabilities/authoring/structure/b2b/lib/stations/stationPatientScript";

/** B2C admin accordion: one section per top-level API model group. */
export function b2cPatientInformationSection(
  extraHistoryBlocks: StationBlock[] = [],
): StationSection {
  return {
    id: "patient_information",
    title: "Patient Information",
    audience: "patient",
    blocks: patientScriptSections(extraHistoryBlocks).flatMap((section) => section.blocks),
  };
}

export function b2cDoctorInformationSection(blocks: StationBlock[]): StationSection {
  return {
    id: "doctor_information",
    title: "Doctor Information",
    audience: "candidate",
    blocks,
  };
}

export function b2cManagementPlanSection(blocks: StationBlock[]): StationSection {
  return {
    id: "management_plan",
    title: "Management Plan",
    audience: "examiner",
    blocks,
  };
}

/** SCA `ScaStationModel.capability` — same strings as B2C admin select. */
export const SCA_CLINICAL_EXPERIENCE_GROUPS: readonly string[] = [
  "Infants, children and young people (under the age of 19)",
  "Mental health (including addiction, alcohol and substance misuse)",
  "People with long term conditions including cancer, multi-morbidity and disability",
  "Older adults including frailty and/or people at end of life",
  "Gender, reproductive and sexual health (including women's, men's, LGBTQ, gynaecology and breast)",
  "Urgent and unscheduled care",
  "People with health disadvantage and vulnerabilities (including veterans, mental capacity difficulties, safeguarding and those with communication difficulties/disability)",
  "Population Health and health promotion (including people with non-acute and/or non-chronic health problems)",
  "Clinical problems not linked to a specific clinical experience group",
  "Ethnicity, culture, diversity, inclusivity",
  "New presentation of undifferentiated disease",
  "Prescribing",
  "Investigation / Results",
  "Professional conversation / Professional dilemma",
];

export function scaClinicalExperienceSection(): StationSection {
  return {
    id: "clinical_experience_groups",
    title: "Clinical Experience Groups",
    audience: "examiner",
    blocks: [
      {
        id: "capability",
        type: "singleSelect",
        role: "examiner",
        label: "Clinical Experience Groups",
        options: [...SCA_CLINICAL_EXPERIENCE_GROUPS],
      },
    ],
  };
}
