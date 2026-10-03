"use client";

import { HiOutlinePresentationChartBar } from "react-icons/hi2";
import { Select, cn, productTokens as t } from "@/foundation/ui";
import { deckSlidesCount, deckVideoUrl, specialtiesOf, type MediaItem } from "@/capabilities/media/api";
import { B2CGroupedRowLink } from "@/foundation/ui/B2CGroupedList";
import { b2cGroupedShell } from "@/foundation/ui/productTokens";

/**
 * The right-hand column: the specialty picker over its list, both filtered server-side.
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
    <div className="space-y-4">
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

      <section>
        <h2 className={cn(t.b2cMonoEyebrow, "px-1 pb-2")}>Presentations</h2>
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
    </div>
  );
}

/** A deck is slides or a recording; the row says which, rather than "0 slides". */
export function deckMeta(deck: MediaItem): string {
  const count = deckSlidesCount(deck);
  if (count !== null && count > 0) return `${count} slides`;
  return deckVideoUrl(deck) ? "video presentation" : "no slides yet";
}
