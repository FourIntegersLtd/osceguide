"use client";

import Link from "next/link";
import { cn, productTokens as t } from "@/foundation/ui";
import { deckSlidesCount, deckVideoUrl, type MediaItem } from "@/capabilities/media/api";

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
  onPick,
  specialty,
  onSpecialtyChange,
  specialtyOptions,
  hasUncategorized,
}: {
  items: MediaItem[];
  currentSlug: string;
  deckHref: (slug: string) => string;
  onPick: () => void;
  specialty: string;
  onSpecialtyChange: (specialty: string) => void;
  specialtyOptions: string[];
  hasUncategorized: boolean;
}) {
  return (
    <>
      {specialtyOptions.length > 0 || hasUncategorized ? (
        <div className="shrink-0 border-b border-b2c-border px-4 py-4 sm:px-5">
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
            {hasUncategorized ? <option value="other">Other / Uncategorized</option> : null}
          </select>
        </div>
      ) : null}

      <div className={cn("min-h-0 flex-1", t.b2cScrollY)}>
        {items.map((deck) => {
          const selected = deck.slug === currentSlug;
          return (
            <Link
              key={deck.id}
              href={deckHref(deck.slug)}
              onClick={onPick}
              scroll={false}
              aria-current={selected ? "page" : undefined}
              className={cn(
                "block w-full border-b border-l-2 border-b2c-border px-4 py-4 text-left transition-colors last:border-b-0 sm:px-5",
                selected
                  ? "border-l-b2c-primary bg-b2c-surface-muted"
                  : "border-l-transparent hover:bg-b2c-surface-muted",
              )}
            >
              <div className={cn(t.b2cPanelListRowTitle, selected && "text-osce-accent")}>
                {deck.title}
              </div>
              <div className={cn(t.b2cPanelCardMeta, "mt-0.5")}>{deckMeta(deck)}</div>
            </Link>
          );
        })}
      </div>
    </>
  );
}

/** A deck is slides or a recording; the row says which, rather than "0 slides". */
export function deckMeta(deck: MediaItem): string {
  const count = deckSlidesCount(deck);
  if (count !== null && count > 0) return `${count} slides`;
  return deckVideoUrl(deck) ? "Video presentation" : "No slides yet";
}
