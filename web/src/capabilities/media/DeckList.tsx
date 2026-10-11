"use client";

import { useEffect, useRef, type ReactNode } from "react";
import {
  HiOutlineMagnifyingGlass,
  HiOutlinePresentationChartBar,
  HiOutlineXMark,
} from "react-icons/hi2";
import { Select, cn, iconSearchInputClassName, productTokens as t } from "@/foundation/ui";
import {
  deckDurationSeconds,
  deckSlidesCount,
  deckVideoUrl,
  specialtiesOf,
  type MediaItem,
} from "@/capabilities/media/api";
import { useStudySearch } from "@/capabilities/media/useStudySearch";
import { clockTime } from "@/capabilities/media/support/text";
import { B2CGroupedRowLink } from "@/foundation/ui/B2CGroupedList";
import { b2cGroupedShell } from "@/foundation/ui/productTokens";

/**
 * The right-hand column: a search over the list, whose header carries the count and the specialty
 * filter. All of it is filtered server-side.
 * The list is a card one viewport tall that scrolls inside, with "Load more" at its foot.
 *
 * `items` is already the specialty-filtered page from the server — the parent
 * fetches a separate, unfiltered sample to build `specialtyOptions`, since an
 * already-filtered result can't tell you what else was on offer.
 */
export function DeckList({
  items,
  currentSlug,
  deckHref,
  specialty,
  onSpecialtyChange,
  specialtyOptions,
  hasUncategorized,
  total,
  footer,
}: {
  items: MediaItem[];
  /** How many presentations match, across every page. */
  total: number | null;
  /** "Load more", drawn inside the card under the last row. */
  footer?: ReactNode;
  currentSlug: string;
  deckHref: (slug: string) => string;
  specialty: string;
  onSpecialtyChange: (specialty: string) => void;
  specialtyOptions: string[];
  hasUncategorized: boolean;
}) {
  const search = useStudySearch("slide_deck");
  const query = search.urlQuery;
  return (
    <div className="flex max-h-[100dvh] min-h-0 flex-col gap-3 lg:h-[100dvh]">
      <DeckSearch term={search.term} onTermChange={search.setTerm} onClear={search.clear} />

      <section className="flex min-h-0 flex-1 flex-col">
        <div className="flex items-center justify-between gap-3 px-1 pb-2">
          <h2 className={cn(t.b2cMonoEyebrow, "min-w-0 truncate")}>
            {(total ?? items.length).toLocaleString()} presentations
          </h2>
          {specialtyOptions.length > 0 || hasUncategorized ? (
            <Select
              aria-label="Filter by specialty"
              selectSize="sm"
              className="w-auto max-w-52"
              value={specialty}
              onChange={(event) => {
                onSpecialtyChange(event.target.value);
                search.clear();
              }}
            >
              <option value="all">All specialties</option>
              {specialtyOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
              {hasUncategorized ? <option value="other">Other or uncategorised</option> : null}
            </Select>
          ) : null}
        </div>
        <div className={cn(b2cGroupedShell, "min-h-0 flex-1 overflow-y-auto")}>
          {items.length === 0 && query !== "" ? (
            <p className="p-4 text-osce-body text-b2c-text-muted">
              No presentations match &ldquo;{query}&rdquo;.
            </p>
          ) : null}
          {items.map((deck) => (
            <B2CGroupedRowLink
              key={deck.id}
              href={deckHref(deck.slug)}
              scroll={false}
              active={deck.slug === currentSlug}
              className={deck.slug === currentSlug ? "bg-b2c-secondary" : undefined}
              icon={HiOutlinePresentationChartBar}
              title={deck.title}
              meta={[specialtiesOf(deck)[0], deckMeta(deck)].filter(Boolean).join(" · ")}
            />
          ))}
          {footer}
        </div>
      </section>
    </div>
  );
}

/** Searches as you type (the URL follows after a pause); × clears it and keeps the specialty. */
function DeckSearch({
  term,
  onTermChange,
  onClear,
}: {
  term: string;
  onTermChange: (term: string) => void;
  onClear: () => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  // The list can swap for the "no matches" view while someone types; carry the focus across.
  useEffect(() => {
    if (term !== "") input.current?.focus();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <form role="search" onSubmit={(event) => event.preventDefault()} className="relative w-full">
      <HiOutlineMagnifyingGlass
        className="pointer-events-none absolute left-3.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-osce-ink-400"
        aria-hidden
      />
      <input
        ref={input}
        type="search"
        placeholder="Search presentations"
        value={term}
        onChange={(event) => onTermChange(event.target.value)}
        aria-label="Search presentations"
        className={cn(iconSearchInputClassName, "pr-10 text-left")}
      />
      {term !== "" ? (
        <button
          type="button"
          onClick={onClear}
          className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-osce-ink-400 transition-colors hover:bg-osce-border-light hover:text-osce-ink-600"
          aria-label="Clear search"
        >
          <HiOutlineXMark className="h-3.5 w-3.5" aria-hidden />
        </button>
      ) : null}
    </form>
  );
}

/** A deck is slides or a recording; the row says which, rather than "0 slides". */
export function deckMeta(deck: MediaItem): string {
  const count = deckSlidesCount(deck);
  const seconds = deckDurationSeconds(deck);
  const length = seconds === null ? null : clockTime(seconds);
  if (count !== null && count > 0) return [`${count} slides`, length].filter(Boolean).join(" · ");
  return deckVideoUrl(deck) ? (length ?? "video presentation") : "no slides yet";
}
