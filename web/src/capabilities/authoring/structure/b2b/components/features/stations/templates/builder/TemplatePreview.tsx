"use client";

import { useAssessWords } from "@/capabilities/assess-words";
import { BlockPreviewContent } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/BlockPreviewContent";
import { stationAudiences, sectionAudience } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import type { StationSection, StationStructure } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import { boardCard, boardPad } from "@/foundation/ui/boardKit";

function SectionPreview({ section }: { section: StationSection }) {
  return (
    <article className={`${boardCard} flex flex-col gap-3 p-4`}>
      <header>
        <h4 className="text-assess-label font-semibold text-ink">{section.title || "Untitled section"}</h4>
        {section.description ? <p className="text-assess-meta text-ink-subtle">{section.description}</p> : null}
      </header>
      {section.blocks.length === 0 ? (
        <p className="text-assess-meta text-ink-subtle">No fields yet.</p>
      ) : (
        section.blocks.map((block) => (
          <div key={block.id} className="space-y-1.5">
            <BlockPreviewContent block={block} />
          </div>
        ))
      )}
    </article>
  );
}

/**
 * The layout as the people filling it in will see it. A station layout is grouped by who each part is
 * written for (patient, candidate, examiner, faculty), in the order they are read; a feedback form is its
 * sections in order.
 */
export function TemplatePreview({ kind, value }: { kind: TemplateKind; value: StationStructure }) {
  const w = useAssessWords();
  if (value.sections.length === 0) {
    return (
      <div className={boardPad}>
        <p className="text-assess-meta text-ink-subtle">Add a section to see the preview.</p>
      </div>
    );
  }
  if (kind !== "station") {
    return (
      <div className={`${boardPad} !bg-surface-raised`}>
        {value.sections.map((section) => (
          <SectionPreview key={section.id} section={section} />
        ))}
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      {stationAudiences(w).map((audience) => {
        const sections = value.sections.filter((s) => sectionAudience(s) === audience.id);
        if (sections.length === 0) return null;
        const Icon = audience.icon;
        return (
          <section key={audience.id} aria-label={audience.label} className={`${boardPad} !bg-surface-raised`}>
            <header className="flex items-start gap-2.5">
              <Icon aria-hidden className="mt-0.5 h-5 w-5 shrink-0 text-ink-subtle" />
              <div>
                <h3 className="text-assess-state-title font-semibold text-ink">{audience.label}</h3>
                <p className="text-assess-meta text-ink-subtle">{audience.description}</p>
              </div>
            </header>
            {sections.map((section) => (
              <SectionPreview key={section.id} section={section} />
            ))}
          </section>
        );
      })}
    </div>
  );
}
