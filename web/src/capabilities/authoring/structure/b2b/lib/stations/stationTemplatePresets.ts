import type {
  StationStructure,
  StationTemplateStartPoint,
} from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { startPointForProfileKey } from "@/capabilities/authoring/structure/b2b/lib/stations/generationProfileKeys";
import { scaFeedbackPresetStructure } from "@/capabilities/authoring/structure/b2b/lib/stations/scaFeedbackPresetStructure";
import { asterixPresetStructure } from "@/capabilities/authoring/structure/b2b/lib/stations/asterixPreset";
import { plabPresetStructure } from "@/capabilities/authoring/structure/b2b/lib/stations/plabPreset";
import { scaPresetStructure } from "@/capabilities/authoring/structure/b2b/lib/stations/scaPreset";
import { orthoPresetStructure } from "@/capabilities/authoring/structure/b2b/lib/stations/stationOrthoPreset";
import { cascStationTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/cascStation";
import { cascFeedbackTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/cascFeedback";
import { plabFeedbackTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/plabFeedback";
import { orthoCommunicationStationTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/orthoCommunicationStation";
import { orthoPortfolioStationTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/orthoPortfolioStation";
import { orthoPrioritisationStationTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/orthoPrioritisationStation";
import { orthoFeedbackTemplateV1 } from "@/capabilities/authoring/structure/b2b/lib/stations/v1/orthoFeedback";

export { asterixPresetStructure, orthoPresetStructure, plabPresetStructure, scaPresetStructure };

export function newId(prefix: string) {
  return `${prefix}_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

/** One patient section to start from; sections for the candidate and examiner are added as needed. */
export function blankStructure(): StationStructure {
  return {
    schemaVersion: 1,
    layout: { persona: "patient" },
    sections: [
      {
        id: newId("sec"),
        title: "Who the patient is",
        audience: "patient",
        blocks: [
          { id: newId("blk"), type: "longText", role: "persona", label: "Patient description" },
        ],
      },
    ],
  };
}

const EXAM_STATION_START: Record<string, StationTemplateStartPoint> = {
  sca: "sca",
  plab: "plab",
  casc: "casc",
  ortho: "ortho",
};

/** Default station layout when authoring with ?exam= on the new-template URL. */
export function defaultStartPointForExam(
  examCode: string | null | undefined,
): StationTemplateStartPoint | null {
  if (!examCode) return null;
  return EXAM_STATION_START[examCode.trim().toLowerCase()] ?? null;
}

/** Default sections/fields for a generation profile, or null for Custom / unknown keys. */
export function structureFromGenerationProfileKey(
  profileKey: string,
): StationStructure | null {
  const startPoint = startPointForProfileKey(profileKey);
  if (!startPoint) return null;
  const structure = structureFromStartPoint(startPoint);
  return {
    ...structure,
    generation: {
      ...structure.generation,
      profileKey: profileKey.trim(),
    },
  };
}

export function structureFromStartPoint(
  startPoint: StationTemplateStartPoint,
): StationStructure {
  if (startPoint === "asterix") return asterixPresetStructure();
  if (startPoint === "sca") return scaPresetStructure();
  if (startPoint === "plab") return plabPresetStructure();
  if (startPoint === "casc") return cascStationTemplateV1();
  if (startPoint === "ortho") return orthoPresetStructure();
  if (startPoint === "ortho_prioritisation") return orthoPrioritisationStationTemplateV1();
  if (startPoint === "ortho_communication") return orthoCommunicationStationTemplateV1();
  if (startPoint === "ortho_portfolio") return orthoPortfolioStationTemplateV1();
  return blankStructure();
}

/** Feedback template layouts per exam marking model. */
export function feedbackStructureFromStartPoint(
  startPoint: StationTemplateStartPoint,
): StationStructure {
  if (startPoint === "sca") return scaFeedbackPresetStructure();
  if (startPoint === "plab") return plabFeedbackTemplateV1();
  if (startPoint === "casc") return cascFeedbackTemplateV1();
  if (startPoint === "ortho") return orthoFeedbackTemplateV1();
  return blankStructure();
}
