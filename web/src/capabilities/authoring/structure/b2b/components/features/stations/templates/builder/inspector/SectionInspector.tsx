import { useAssessWords } from "@/capabilities/assess-words";
import type { StationSection, StationSectionAudience } from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { sectionAudience, stationAudiences } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import { boardBtn } from "@/foundation/ui/boardKit";

/** The body of the board's "Section" card: who it is written for and removing it. Title and description are edited on the section itself. */
export function SectionInspector({
  kind,
  section,
  caption,
  onAudienceChange,
  onRemove,
}: {
  kind: TemplateKind;
  section: StationSection;
  caption: string;
  onAudienceChange: (audience: StationSectionAudience) => void;
  onRemove: () => void;
}) {
  const w = useAssessWords();
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
            {stationAudiences(w).map((a) => (
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
      <button type="button" className={`${boardBtn("danger", true)} self-start`} onClick={onRemove}>
        Remove section
      </button>
    </>
  );
}
