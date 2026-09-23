import type { StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { cascStationTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/cascStation";
import { orthoClinicalStationTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/orthoClinicalStation";
import { orthoCommunicationStationTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/orthoCommunicationStation";
import { orthoPortfolioStationTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/orthoPortfolioStation";
import { orthoPrioritisationStationTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/orthoPrioritisationStation";
import { plabStationTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/plabStation";
import { scaStationTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/scaStation";

const ORTHO_TEMPLATES: Record<string, () => StationStructure> = {
  clinical: orthoClinicalStationTemplateV1,
  communication: orthoCommunicationStationTemplateV1,
  prioritisation: orthoPrioritisationStationTemplateV1,
  portfolio: orthoPortfolioStationTemplateV1,
};

/** B2C admin accordion layout for imported library stations (no template_version_id). */
export function legacyB2cStationStructure(
  examCode: string,
  content: Record<string, unknown>,
): StationStructure | null {
  const exam = examCode.trim().toLowerCase();
  switch (exam) {
    case "sca":
      return scaStationTemplateV1();
    case "plab":
      return plabStationTemplateV1();
    case "casc":
      return cascStationTemplateV1();
    case "ortho": {
      const type = String(content.station_type ?? "clinical").toLowerCase();
      const build = ORTHO_TEMPLATES[type] ?? orthoClinicalStationTemplateV1;
      return build();
    }
    default:
      return null;
  }
}

export function isLegacyB2cStationContent(content: Record<string, unknown>): boolean {
  return (
    typeof content.patient_information === "object" ||
    typeof content.doctor_information === "object" ||
    typeof content.management_plan === "object" ||
    typeof content.station_type === "string"
  );
}
