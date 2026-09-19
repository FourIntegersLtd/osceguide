"use client";

import Link from "next/link";
import { useState } from "react";
import { HiOutlineBars3, HiOutlineXMark } from "react-icons/hi2";
import {
  AsyncBoundary,
  B2CPageHeader,
  B2CPanelCard,
  B2CPanelCardHeader,
  B2CSegmentedTabs,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import {
  aboutText,
  deckSlides,
  deckVideoUrl,
  listAllMedia,
  specialtiesOf,
  type MediaItem,
} from "@/capabilities/media/api";
import { DeckStage } from "@/capabilities/media/DeckStage";

/**
 * A slide deck, beside the rest of the presentations.
 *
 * The retiring client held the selected deck in component state, so a
 * presentation had no address of its own and could not be linked to or
 * reloaded. Each row is a link now and the deck being read is the one in the
 * URL — the same two-pane layout, with the browser doing the state.
 */
export function DeckView({ item, hrefFor }: { item: MediaItem; hrefFor: (path: string) => string }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tab, setTab] = useState<"about" | "conversation">("about");
  const decks = useAsync((signal) => listAllMedia("slide_deck", signal), []);

  return (
    <div className="w-full text-left">
      <B2CPageHeader
        title="Slides"
        subtitle="Video presentations by topic"
        back={{ href: hrefFor("/library"), label: "Study material" }}
      />

      <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
        {!sidebarOpen && (
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className={cn(t.b2cGhostButton, "w-full justify-start lg:hidden")}
            aria-label="Open presentations list"
          >
            <HiOutlineBars3 className="h-4 w-4 shrink-0 text-osce-accent" aria-hidden />
            <span className="truncate">{item.title}</span>
          </button>
        )}

        {sidebarOpen && (
          <div
            className="fixed inset-0 z-30 bg-black/55 backdrop-blur-md lg:hidden"
            onClick={() => setSidebarOpen(false)}
            aria-hidden
          />
        )}

        <aside
          className={cn(
            "fixed inset-y-0 left-0 z-40 flex w-[min(85vw,20rem)] flex-col lg:static lg:z-auto lg:w-80 lg:shrink-0 lg:self-start",
            "top-16 h-[calc(100dvh-4rem)] lg:top-auto lg:h-auto lg:max-h-none",
            "transition-transform duration-200 lg:translate-x-0",
            sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
          )}
        >
          <B2CPanelCard className="mt-0 flex h-full min-h-0 flex-col overflow-hidden lg:h-auto lg:max-h-[calc(100dvh-10rem)]">
            <B2CPanelCardHeader className="shrink-0 justify-between">
              <span>Presentations</span>
              <button
                type="button"
                onClick={() => setSidebarOpen(false)}
                className={cn(t.b2cIconButton, "lg:hidden")}
                aria-label="Close presentations list"
              >
                <HiOutlineXMark className="h-5 w-5" aria-hidden />
              </button>
            </B2CPanelCardHeader>

            <AsyncBoundary state={decks}>
              {(items) => (
                <DeckList
                  items={items}
                  currentSlug={item.slug}
                  hrefFor={hrefFor}
                  onPick={() => setSidebarOpen(false)}
                />
              )}
            </AsyncBoundary>
          </B2CPanelCard>
        </aside>

        <B2CPanelCard className="mt-0 flex min-w-0 flex-1 flex-col">
          <B2CPanelCardHeader className="truncate">{item.title}</B2CPanelCardHeader>

          <div className="flex min-h-[280px] items-center justify-center bg-osce-surface p-4 sm:p-6 lg:min-h-[360px]">
            <DeckStage item={item} />
          </div>

          <div className="flex-shrink-0 border-t border-b2c-border bg-osce-surface">
            <div className="px-4 pt-4 sm:px-6">
              <B2CSegmentedTabs
                items={[
                  { id: "about", label: "About" },
                  { id: "conversation", label: "Conversation" },
                ]}
                value={tab}
                onChange={setTab}
                aria-label="Presentation details"
              />
            </div>
            <div className={cn("max-h-56 px-4 py-4 sm:px-6", t.b2cScrollY)}>
              <p className={t.b2cBodyText}>
                {tab === "about"
                  ? (aboutText(item) ?? "No description.")
                  : "No conversation available for this presentation."}
              </p>
            </div>
          </div>
        </B2CPanelCard>
      </div>
    </div>
  );
}

/**
 * The sidebar list, with the specialty filter the old screen had.
 *
 * The filter was a query parameter on the retiring backend; `GET /media` has
 * no specialty facet, so it reads what the authoring payload carries and hides
 * itself when nothing does — see `docs/port-gaps.md`.
 */
function DeckList({
  items,
  currentSlug,
  hrefFor,
  onPick,
}: {
  items: MediaItem[];
  currentSlug: string;
  hrefFor: (path: string) => string;
  onPick: () => void;
}) {
  const [specialty, setSpecialty] = useState("all");
  const options = [...new Set(items.flatMap(specialtiesOf))].sort();
  const visible =
    specialty === "all" ? items : items.filter((deck) => specialtiesOf(deck).includes(specialty));

  return (
    <>
      {options.length > 0 ? (
        <div className="shrink-0 border-b border-b2c-border px-4 py-4 sm:px-5">
          <label htmlFor="deck-specialty-filter" className={t.b2cFieldLabel}>
            Filter by specialty
          </label>
          <select
            id="deck-specialty-filter"
            value={specialty}
            onChange={(event) => setSpecialty(event.target.value)}
            className={cn(t.b2cInputBase, "mt-1.5")}
          >
            <option value="all">All specialties</option>
            {options.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
        </div>
      ) : null}

      <div className={cn("min-h-0 flex-1", t.b2cScrollY)}>
        {visible.map((deck) => {
          const selected = deck.slug === currentSlug;
          return (
            <Link
              key={deck.id}
              href={hrefFor(`/library/${deck.slug}`)}
              onClick={onPick}
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
function deckMeta(deck: MediaItem): string {
  const count = deckSlides(deck).length;
  if (count > 0) return `${count} slides`;
  return deckVideoUrl(deck) ? "Video presentation" : "No slides yet";
}
