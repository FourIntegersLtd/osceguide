"use client";

import type { ReactNode } from "react";
import { HiOutlinePresentationChartBar } from "react-icons/hi2";
import { Select, cn, productTokens as t } from "@/foundation/ui";
import {
  deckDurationSeconds,
  deckSlidesCount,
  deckVideoUrl,
  specialtiesOf,
  type MediaItem,
} from "@/capabilities/media/api";
import { clockTime } from "@/capabilities/media/support/text";
import { B2CGroupedRowLink } from "@/foundation/ui/B2CGroupedList";
import { b2cGroupedShell } from "@/foundation/ui/productTokens";

/**
 * The right-hand column: the specialty picker over its list, both filtered server-side.
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
  return (
    <div className="flex max-h-[100dvh] min-h-0 flex-col gap-4 lg:h-[100dvh]">
      {specialtyOptions.length > 0 || hasUncategorized ? (
        <Select
          label="Filter by specialty"
          value={specialty}
          onChange={(event) => onSpecialtyChange(event.target.value)}
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

      <section className="flex min-h-0 flex-1 flex-col">
        <h2 className={cn(t.b2cMonoEyebrow, "px-1 pb-2")}>
          {(total ?? items.length).toLocaleString()} presentations
        </h2>
        <div className={cn(b2cGroupedShell, "min-h-0 flex-1 overflow-y-auto")}>
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

/** A deck is slides or a recording; the row says which, rather than "0 slides". */
export function deckMeta(deck: MediaItem): string {
  const count = deckSlidesCount(deck);
  const seconds = deckDurationSeconds(deck);
  const length = seconds === null ? null : clockTime(seconds);
  if (count !== null && count > 0) return [`${count} slides`, length].filter(Boolean).join(" · ");
  return deckVideoUrl(deck) ? (length ?? "video presentation") : "no slides yet";
}
