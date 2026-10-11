"use client";

import { useState } from "react";
import { LuStethoscope } from "react-icons/lu";
import {
  B2CEmptyState,
  B2CSegmentedTabs,
} from "@/foundation/ui";
import { specialtiesOf, type MediaItem } from "@/capabilities/media/api";
import { studyTabPathForSlug } from "@/capabilities/media/studyPaths";
import { B2CHero } from "@/foundation/ui/B2CHero";
import { B2CGroupedRowLink, B2CGroupedSection } from "@/foundation/ui/B2CGroupedList";

type SummaryView = "az" | "specialty";

/**
 * The A-to-Z: every group listed in order, with letters that jump to their
 * section. The letters are in-page anchors rather than URL state, so browsing
 * the index does not fill the back stack.
 */
export function SummaryIndex({
  items,
  hrefFor,
}: {
  items: MediaItem[];
  hrefFor: (path: string) => string;
}) {
  const [view, setView] = useState<SummaryView>("az");

  const groups = view === "az" ? groupByLetter(items) : groupBySpecialty(items);
  const keys = Object.keys(groups).sort();

  return (
    <div className="space-y-6 text-left">
      <B2CHero
        eyebrow="Revise"
        title="Conditions, written for primary care"
      >
        Each summary has a clinical and a psychosocial side, and you can talk it through with Athena.
      </B2CHero>

      <div className="flex flex-wrap items-center justify-between gap-4">
        <B2CSegmentedTabs
          items={[
            { id: "az", label: "A to Z" },
            { id: "specialty", label: "Specialty" },
          ]}
          value={view}
          onChange={setView}
          aria-label="Summary view"
        />
      </div>

      {keys.length === 0 && view === "specialty" ? (
        <B2CEmptyState
          icon={LuStethoscope}
          title="Nothing is filed under a specialty yet"
          description="Summaries appear here once they are published with one."
        />
      ) : null}

      {view === "az" && keys.length > 1 ? (
        <nav aria-label="Jump to letter" className="flex flex-wrap gap-0.5">
          {keys.map((key) => (
            <a
              key={key}
              href={`#summary-${key}`}
              className="flex h-8 min-w-8 items-center justify-center rounded-osce-md px-2 text-osce-meta font-medium text-b2c-text-muted transition-colors hover:bg-b2c-surface-muted hover:text-osce-ink-900"
            >
              {key}
            </a>
          ))}
        </nav>
      ) : null}

      {keys.map((key) => (
        <B2CGroupedSection key={key} id={`summary-${key}`} eyebrow={key} className="scroll-mt-24">
          {(groups[key] ?? []).map((item) => {
            const specialty = specialtiesOf(item)[0];
            return (
              <B2CGroupedRowLink
                key={item.id}
                href={hrefFor(studyTabPathForSlug("summary", item.slug))}
                icon={LuStethoscope}
                title={item.title}
                meta={view === "az" && specialty ? specialty : undefined}
                trailing={item.locked ? <span className="text-osce-meta text-b2c-text-muted">Locked</span> : undefined}
              />
            );
          })}
        </B2CGroupedSection>
      ))}
    </div>
  );
}

function groupByLetter(items: MediaItem[]): Record<string, MediaItem[]> {
  const sorted = [...items].sort((a, b) => a.title.localeCompare(b.title));
  return sorted.reduce<Record<string, MediaItem[]>>((acc, item) => {
    const letter = item.title.charAt(0).toUpperCase();
    (acc[letter] ??= []).push(item);
    return acc;
  }, {});
}

/**
 * An item with several specialties appears under each of them, as it did
 * before. Items with none are left out entirely rather than gathered under
 * "Unknown": on this backend that is every item, and a single bucket holding
 * the whole library is worse than an empty state that says so.
 */
function groupBySpecialty(items: MediaItem[]): Record<string, MediaItem[]> {
  return items.reduce<Record<string, MediaItem[]>>((acc, item) => {
    for (const specialty of specialtiesOf(item)) {
      (acc[specialty] ??= []).push(item);
    }
    return acc;
  }, {});
}
