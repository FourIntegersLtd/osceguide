"use client";

import { useState } from "react";
import { HiOutlinePresentationChartBar } from "react-icons/hi2";
import {
  B2CPageHeader,
  B2CSegmentedTabs,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import { aboutText, type MediaItem } from "@/capabilities/media/api";
import { DeckList, deckMeta } from "@/capabilities/media/DeckList";
import { DeckStage } from "@/capabilities/media/DeckStage";
import { STUDY_KIND_LABEL, studyListPath } from "@/capabilities/media/studyPaths";
import { useRecordView } from "@/capabilities/account/useRecordView";
import { DiscussWithAthena } from "@/capabilities/help/DiscussWithAthena";

export function SlidesWorkspace({
  selected,
  decks,
  deckHref,
  hrefFor,
  showPageHeader = false,
  showBackLink = false,
  specialty,
  onSpecialtyChange,
  specialtyOptions,
  hasUncategorized,
}: {
  selected: MediaItem;
  decks: MediaItem[];
  deckHref: (slug: string) => string;
  hrefFor: (path: string) => string;
  showPageHeader?: boolean;
  showBackLink?: boolean;
  specialty: string;
  onSpecialtyChange: (specialty: string) => void;
  specialtyOptions: string[];
  hasUncategorized: boolean;
}) {
  useRecordView(
    selected.locked
      ? null
      : { kind: "viewed", ref_kind: "slide_deck", ref_id: selected.slug, title: selected.title, exam_code: selected.exam_code },
  );
  const [tab, setTab] = useState<"about" | "conversation">("about");

  return (
    <div className="w-full text-left">
      {showPageHeader ? (
        <B2CPageHeader
          title="Slides"
          subtitle="Video presentations by topic."
          back={
            showBackLink
              ? { href: hrefFor(studyListPath("slide_deck")), label: STUDY_KIND_LABEL.slide_deck }
              : undefined
          }
        />
      ) : null}

      <div className="space-y-6">
        <section className="overflow-hidden rounded-osce-lg border border-osce-border bg-osce-surface">
          <header className="flex flex-wrap items-center gap-3 px-5 pb-3 pt-[18px]">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-control bg-b2c-surface-muted text-b2c-text-muted">
              <HiOutlinePresentationChartBar className="h-4 w-4" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="truncate text-osce-subheading font-semibold text-osce-ink-900">{selected.title}</h2>
              <p className="text-osce-meta text-b2c-text-muted">{deckMeta(selected)}</p>
            </div>
            <DiscussWithAthena topic={{ title: selected.title, kind: "slide_deck", slug: selected.slug }} />
          </header>

          <div className="flex min-h-[280px] items-center justify-center border-y border-osce-border-light p-4 sm:p-6 lg:min-h-[360px]">
            <DeckStage item={selected} />
          </div>

          <div className="px-5 pb-5 pt-4">
            <B2CSegmentedTabs
              items={[
                { id: "about", label: "About" },
                { id: "conversation", label: "Conversation" },
              ]}
              value={tab}
              onChange={setTab}
              aria-label="Presentation details"
            />
            <p className={cn("max-h-56", t.b2cScrollY, t.b2cBodyText)}>
              {tab === "about"
                ? (aboutText(selected) ?? "No description.")
                : "No conversation available for this presentation."}
            </p>
          </div>
        </section>

        <DeckList
          items={decks}
          currentSlug={selected.slug}
          deckHref={deckHref}
          specialty={specialty}
          onSpecialtyChange={onSpecialtyChange}
          specialtyOptions={specialtyOptions}
          hasUncategorized={hasUncategorized}
        />
      </div>
    </div>
  );
}
