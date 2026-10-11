"use client";

import type { ReactNode } from "react";
import { HiOutlineChevronLeft } from "react-icons/hi2";
import {
  B2CPageHeader,
  B2CSkeleton,
  ButtonLink,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import { aboutText, deckHeading, deckSlides, deckVideoUrl, type MediaItem } from "@/capabilities/media/api";
import { DeckList, deckMeta } from "@/capabilities/media/DeckList";
import { DeckStage } from "@/capabilities/media/DeckStage";
import { STUDY_KIND_LABEL, studyListPath } from "@/capabilities/media/studyPaths";
import type { StudySearch } from "@/capabilities/media/useStudySearch";
import { useRecordView } from "@/capabilities/account/useRecordView";
import { DiscussWithAthena } from "@/capabilities/help/DiscussWithAthena";

/**
 * A presentation beside the list it came from (canvas `train-slides`): the
 * stage, its title and what it is about on the left, the specialty filter and
 * every presentation on the right.
 */
export function SlidesWorkspace({
  selected,
  decks,
  search,
  loading,
  deckHref,
  hrefFor,
  showPageHeader = false,
  showBackLink = false,
  specialty,
  onSpecialtyChange,
  specialtyOptions,
  hasUncategorized,
  total,
  footer,
}: {
  /** The deck on the stage; null while the list is first being read or a search finds none. */
  selected: MediaItem | null;
  search: StudySearch;
  loading: boolean;
  total: number | null;
  footer?: ReactNode;
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
    !selected || selected.locked
      ? null
      : { kind: "viewed", ref_kind: "slide_deck", ref_id: selected.slug, title: selected.title, exam_code: selected.exam_code },
  );

  // Previous and Next walk the list on the right, in its order.
  const position = decks.findIndex((deck) => deck.slug === selected?.slug);
  const previous = position > 0 ? decks[position - 1] : undefined;
  const next = position >= 0 ? decks[position + 1] : undefined;
  // A recording, or nothing yet, fills a 16:9 stage; slides read as a page
  // and take the height they need.
  const framed = !selected || deckVideoUrl(selected) !== null || deckSlides(selected).length === 0;

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

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1.8fr_1fr]">
        <div className="min-w-0 space-y-4">
          <div
            className={cn(
              "overflow-hidden rounded-osce-2xl bg-osce-tone-history-bg",
              framed ? "flex aspect-video items-center justify-center" : "p-4",
            )}
          >
            {selected ? <DeckStage item={selected} /> : loading ? <B2CSkeleton.Card lines={4} /> : null}
          </div>
          {selected ? <SelectedDeck selected={selected} previous={previous} next={next} deckHref={deckHref} /> : null}
        </div>

        <DeckList
          items={decks}
          search={search}
          loading={loading}
          currentSlug={selected?.slug ?? ""}
          deckHref={deckHref}
          specialty={specialty}
          onSpecialtyChange={onSpecialtyChange}
          specialtyOptions={specialtyOptions}
          hasUncategorized={hasUncategorized}
          total={total}
          footer={footer}
        />
      </div>
    </div>
  );
}

/** Under the stage: the deck's topic, its title and length, Previous and Next, and what it is about. */
function SelectedDeck({
  selected,
  previous,
  next,
  deckHref,
}: {
  selected: MediaItem;
  previous: MediaItem | undefined;
  next: MediaItem | undefined;
  deckHref: (slug: string) => string;
}) {
  const { title, subtitle } = deckHeading(selected);
  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h2 className="text-osce-title font-semibold text-osce-ink-900">{title}</h2>
          <p className="text-osce-meta text-b2c-text-muted">
            {[subtitle, deckMeta(selected)].filter(Boolean).join(" · ")}
          </p>
        </div>
        <div className="flex shrink-0 gap-2">
          {previous ? (
            <ButtonLink href={deckHref(previous.slug)} scroll={false} variant="secondary" className="gap-1.5">
              <HiOutlineChevronLeft className="h-4 w-4" aria-hidden />
              Previous
            </ButtonLink>
          ) : null}
          {next ? (
            <ButtonLink href={deckHref(next.slug)} scroll={false} variant="secondary">
              Next
            </ButtonLink>
          ) : null}
        </div>
      </div>
      <p className={cn("max-h-56", t.b2cScrollY, t.b2cBodyText)}>{aboutText(selected) ?? "No description."}</p>
      <DiscussWithAthena topic={{ title: selected.title, kind: "slide_deck", slug: selected.slug }} />
    </>
  );
}
