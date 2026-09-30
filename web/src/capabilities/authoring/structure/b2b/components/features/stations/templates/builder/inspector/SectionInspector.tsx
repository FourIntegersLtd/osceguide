import type {
  StationSection,
  StationSectionAudience,
} from "@/capabilities/authoring/structure/b2b/types/b2bStationTemplateTypes";
import type { TemplateKind } from "@/capabilities/authoring/structure/b2b/lib/stations/blockTypeLabels";
import { sectionAudience, STATION_AUDIENCES } from "@/capabilities/authoring/structure/b2b/lib/stations/blockRoles";
import { b2bInputBase } from "@/capabilities/authoring/structure/b2b/theme/b2bUi";
import { HiOutlineTrash } from "react-icons/hi2";
import {
  BuilderButton,
  builderUi,
  ToneBadge,
  toneForAudience,
} from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/builderChrome";
import { inspectorLabel } from "@/capabilities/authoring/structure/b2b/components/features/stations/templates/builder/inspector/MoreOptions";

const inspectorInput = `${b2bInputBase} py-2 text-osce-body`;

export function SectionInspector({
  kind,
  section,
  onPatch,
  onAudienceChange,
  onRemove,
}: {
  kind: TemplateKind;
  section: StationSection;
  onPatch: (patch: Partial<StationSection>) => void;
  onAudienceChange: (audience: StationSectionAudience) => void;
  onRemove: () => void;
}) {
  const audience = sectionAudience(section);
  return (
    <div className="space-y-4">
      {kind === "station" ? (
        <div>
          <p id="section-inspector-audience" className={inspectorLabel}>
            Written for
          </p>
          <div className="space-y-1.5" role="radiogroup" aria-labelledby="section-inspector-audience">
            {STATION_AUDIENCES.map((a) => {
              const active = a.id === audience;
              const Icon = a.icon;
              return (
                <button
                  key={a.id}
                  type="button"
                  role="radio"
                  aria-checked={active}
                  onClick={() => onAudienceChange(a.id)}
                  className={[
                    "flex w-full items-start gap-3 rounded-xl border px-3 py-2.5 text-left transition-colors",
                    builderUi.focusRing,
                    active
                      ? "border-osce-accent-subtle bg-osce-accent-muted/60"
                      : "border-osce-border bg-osce-surface hover:bg-osce-canvas",
                  ].join(" ")}
                >
                  <ToneBadge tone={toneForAudience[a.id]} size="sm">
                    <Icon aria-hidden />
                  </ToneBadge>
                  <span className="min-w-0">
                    <span className="block text-osce-body font-medium text-osce-ink-700">
                      {a.label}
                    </span>
                    <span className="block text-osce-caption leading-snug text-osce-ink-400">
                      {a.description}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}
      <div>
        <label htmlFor="section-inspector-title" className={inspectorLabel}>Title</label>
        <input
          id="section-inspector-title"
          value={section.title}
          onChange={(e) => onPatch({ title: e.target.value })}
          className={inspectorInput}
        />
      </div>
      <div>
        <label htmlFor="section-inspector-description" className={inspectorLabel}>Description</label>
        <input
          id="section-inspector-description"
          value={section.description || ""}
          onChange={(e) => onPatch({ description: e.target.value })}
          className={inspectorInput}
          placeholder="Shown above this section (optional)"
        />
      </div>
      <BuilderButton variant="danger" size="sm" onClick={onRemove}>
        <HiOutlineTrash className="h-4 w-4" aria-hidden />
        Remove section
      </BuilderButton>
    </div>
  );
}
