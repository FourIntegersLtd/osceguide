"use client";

import { HiOutlinePresentationChartBar } from "react-icons/hi2";
import { cn, productTokens as t } from "@/foundation/ui";
import { deckSlidesCount, deckVideoUrl, specialtiesOf, type MediaItem } from "@/capabilities/media/api";
import { B2CGroupedRowLink } from "@/foundation/ui/B2CGroupedList";
import { b2cGroupedShell } from "@/foundation/ui/productTokens";

/**
 * The specialty picker and its list, both filtered server-side.
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
}: {
  items: MediaItem[];
  currentSlug: string;
  deckHref: (slug: string) => string;
  specialty: string;
  onSpecialtyChange: (specialty: string) => void;
  specialtyOptions: string[];
  hasUncategorized: boolean;
}) {
  return (
    <section className="space-y-3">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <p className={t.b2cMonoEyebrow}>Presentations</p>
        {specialtyOptions.length > 0 || hasUncategorized ? (
          <div className="w-full sm:w-64">
            <label htmlFor="deck-specialty-filter" className={t.b2cFieldLabel}>
              Filter by specialty
            </label>
            <select
              id="deck-specialty-filter"
              value={specialty}
              onChange={(event) => onSpecialtyChange(event.target.value)}
              className={cn(t.b2cInputBase, "mt-1.5")}
            >
              <option value="all">All specialties</option>
              {specialtyOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
              {hasUncategorized ? <option value="other">Other or uncategorised</option> : null}
            </select>
          </div>
        ) : null}
      </div>

      <div className={b2cGroupedShell}>
        {items.map((deck) => (
          <B2CGroupedRowLink
            key={deck.id}
            href={deckHref(deck.slug)}
            scroll={false}
            active={deck.slug === currentSlug}
            icon={HiOutlinePresentationChartBar}
            title={deck.title}
            meta={[specialtiesOf(deck)[0], deckMeta(deck)].filter(Boolean).join(" · ")}
          />
        ))}
      </div>
    </section>
  );
}

/** A deck is slides or a recording; the row says which, rather than "0 slides". */
export function deckMeta(deck: MediaItem): string {
  const count = deckSlidesCount(deck);
  if (count !== null && count > 0) return `${count} slides`;
  return deckVideoUrl(deck) ? "Video presentation" : "No slides yet";
}
