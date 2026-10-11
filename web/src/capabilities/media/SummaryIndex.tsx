"use client";

import { useState } from "react";
import { LuPodcast, LuStethoscope } from "react-icons/lu";
import { B2CEmptyState, B2CSegmentedTabs, Modal, cn } from "@/foundation/ui";
import { specialtiesOf, type MediaItem } from "@/capabilities/media/api";
import { studyTabPathForSlug } from "@/capabilities/media/studyPaths";
import { B2CGroupedRowLink, B2CGroupedSection } from "@/foundation/ui/B2CGroupedList";
import { SummaryPodcast } from "@/capabilities/media/SummaryView";
import { jumpLinks, summaryGroups, type SummaryView } from "@/capabilities/media/summaryGroups";

/**
 * The A to Z / Specialty tabs and the row of jump links. They sit in the page's sticky
 * header beside the search, so they stay in reach while the list scrolls. The links are
 * in-page anchors rather than URL state, so browsing the index does not fill the back stack.
 */
export function SummaryIndexNav({
  items,
  view,
  onViewChange,
}: {
  items: readonly MediaItem[];
  view: SummaryView;
  onViewChange: (view: SummaryView) => void;
}) {
  const links = jumpLinks(summaryGroups(items, view));
  return (
    <div className="space-y-3">
      <B2CSegmentedTabs
        items={[
          { id: "az", label: "A to Z" },
          { id: "specialty", label: "Specialty" },
        ]}
        value={view}
        onChange={onViewChange}
        aria-label="Summary view"
      />
      {links.length > 0 ? (
        <nav
          aria-label={view === "az" ? "Jump to letter" : "Jump to specialty"}
          className="flex flex-wrap gap-0.5"
        >
          {links.map(({ key, href }) => (
            <a
              key={key}
              href={href}
              className="flex h-8 min-w-8 items-center justify-center rounded-osce-md px-2 text-osce-meta font-medium text-b2c-text-muted transition-colors hover:bg-b2c-surface-muted hover:text-osce-ink-900"
            >
              {key}
            </a>
          ))}
        </nav>
      ) : null}
    </div>
  );
}

/** The list itself: every group in order, each row a link to its summary and a Listen button. */
export function SummaryIndex({
  items,
  view,
  hrefFor,
}: {
  items: MediaItem[];
  view: SummaryView;
  hrefFor: (path: string) => string;
}) {
  const [listening, setListening] = useState<MediaItem | null>(null);
  const groups = summaryGroups(items, view);
  const keys = Object.keys(groups).sort();

  return (
    <div className="space-y-6 text-left">
      {keys.length === 0 && view === "specialty" ? (
        <B2CEmptyState
          icon={LuStethoscope}
          title="Nothing is filed under a specialty yet"
          description="Summaries appear here once they are published with one."
        />
      ) : null}

      {keys.map((key) => (
        <B2CGroupedSection key={key} id={`summary-${key}`} eyebrow={key} className="scroll-mt-48">
          {(groups[key] ?? []).map((item) => {
            const specialty = specialtiesOf(item)[0];
            return (
              <div key={item.id} className="flex items-center border-b border-b2c-border-light last:border-b-0">
                <B2CGroupedRowLink
                  href={hrefFor(studyTabPathForSlug("summary", item.slug))}
                  icon={LuStethoscope}
                  title={item.title}
                  meta={view === "az" && specialty ? specialty : undefined}
                  trailing={item.locked ? <span className="text-osce-meta text-b2c-text-muted">Locked</span> : undefined}
                  className="min-w-0 flex-1 border-b-0"
                />
                <ListenButton item={item} onListen={() => setListening(item)} />
              </div>
            );
          })}
        </B2CGroupedSection>
      ))}

      {listening ? (
        <Modal width="700px" height="fit-content" onClose={() => setListening(null)} title={listening.title}>
          <SummaryPodcast item={listening} />
        </Modal>
      ) : null}
    </div>
  );
}

/** Muted and `aria-disabled` when the summary has no podcast (or its body is locked). */
function ListenButton({ item, onListen }: { item: MediaItem; onListen: () => void }) {
  const enabled = item.has_podcast && !item.locked;
  return (
    <button
      type="button"
      aria-disabled={!enabled}
      aria-label={`Listen to ${item.title}`}
      title={enabled ? undefined : "No podcast for this summary yet"}
      onClick={enabled ? onListen : undefined}
      className={cn(
        "mr-3 flex shrink-0 items-center gap-1.5 rounded-osce-md px-2.5 py-1.5 text-osce-meta font-medium transition-colors",
        enabled
          ? "text-osce-ink-700 hover:bg-b2c-surface-muted hover:text-osce-ink-900"
          : "cursor-not-allowed text-osce-ink-400",
      )}
    >
      <LuPodcast className="h-4 w-4" aria-hidden />
      <span>Listen</span>
    </button>
  );
}
