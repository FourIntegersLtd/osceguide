"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import Modal from "@/foundation/ui/Modal";
import { SectionInspector } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/inspector/SectionInspector";
import { audienceMeta, sectionAudience } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import type { StationSection, StationSectionAudience } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { boardBtn } from "@/foundation/ui/boardKit";

/** The dialog a section card opens for its audience and Remove; its title and description are edited on the card. */
export function SectionSettingsDialog({
  kind,
  section,
  index,
  onAudienceChange,
  onRemove,
  onClose,
}: {
  kind: TemplateKind;
  section: StationSection;
  index: number;
  onAudienceChange: (next: StationSectionAudience) => void;
  onRemove: () => void;
  onClose: () => void;
}) {
  const w = useAssessWords();
  return (
    <Modal variant="board" labelledBy="section-settings-title" width="28rem" onClose={onClose}>
      <div className="flex flex-col gap-3.5">
        <h2 id="section-settings-title" className="text-assess-state-title font-semibold text-ink">
          Section settings
        </h2>
        <SectionInspector
          kind={kind}
          section={section}
          caption={kind === "station" ? audienceMeta(sectionAudience(section), w).label : `Section ${index + 1}`}
          onAudienceChange={onAudienceChange}
          onRemove={onRemove}
        />
        <button type="button" className={boardBtn("primary")} onClick={onClose}>
          Done
        </button>
      </div>
    </Modal>
  );
}
