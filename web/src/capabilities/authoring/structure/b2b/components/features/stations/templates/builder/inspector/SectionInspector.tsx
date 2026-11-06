import type { StationSection, StationSectionAudience } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { sectionAudience, STATION_AUDIENCES } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import { boardBtn, boardInput } from "@/foundation/ui/boardKit";
import { inspectorLabel } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/inspector/MoreOptions";

/** The body of the board's "Section" card: who it is written for, its title and description, and removing it. */
export function SectionInspector({
  kind,
  section,
  caption,
  onPatch,
  onAudienceChange,
  onRemove,
}: {
  kind: TemplateKind;
  section: StationSection;
  caption: string;
  onPatch: (patch: Partial<StationSection>) => void;
  onAudienceChange: (audience: StationSectionAudience) => void;
  onRemove: () => void;
}) {
  const audience = sectionAudience(section);
  return (
    <>
      <p className="text-assess-meta text-ink-subtle">{caption}</p>
      {kind === "station" ? (
        <>
          <p id="section-inspector-audience" className="text-assess-eyebrow uppercase text-ink-subtle">
            Written for
          </p>
          <div role="radiogroup" aria-labelledby="section-inspector-audience" className="flex flex-col gap-3.5">
            {STATION_AUDIENCES.map((a) => (
              <label key={a.id} className="flex min-h-8 cursor-pointer items-start gap-2.5 text-assess-label text-ink">
                <input
                  type="radio"
                  name="section-inspector-audience"
                  checked={a.id === audience}
                  onChange={() => onAudienceChange(a.id)}
                  className="mt-0.5 h-[18px] w-[18px] accent-osce-accent"
                />
                <span>
                  <b className="font-semibold">{a.label}</b>
                  <span className="block text-assess-meta text-ink-subtle">{a.description}</span>
                </span>
              </label>
            ))}
          </div>
        </>
      ) : null}
      <div>
        <label htmlFor="section-inspector-title" className={inspectorLabel}>Title</label>
        <input
          id="section-inspector-title"
          value={section.title}
          onChange={(e) => onPatch({ title: e.target.value })}
          className={boardInput}
        />
      </div>
      <div>
        <label htmlFor="section-inspector-description" className={inspectorLabel}>Description</label>
        <input
          id="section-inspector-description"
          value={section.description || ""}
          onChange={(e) => onPatch({ description: e.target.value })}
          className={boardInput}
          placeholder="Shown above this section (optional)"
        />
      </div>
      <button type="button" className={`${boardBtn("danger", true)} self-start`} onClick={onRemove}>
        Remove section
      </button>
    </>
  );
}
