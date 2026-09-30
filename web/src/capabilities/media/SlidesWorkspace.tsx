"use client";

import { useState } from "react";
import { HiOutlineBars3, HiOutlineXMark } from "react-icons/hi2";
import {
  B2CPageHeader,
  B2CPanelCard,
  B2CPanelCardHeader,
  B2CSegmentedTabs,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import { aboutText, type MediaItem } from "@/capabilities/media/api";
import { DeckList } from "@/capabilities/media/DeckList";
import { DeckStage } from "@/capabilities/media/DeckStage";
import { STUDY_KIND_LABEL, studyListPath } from "@/capabilities/media/studyPaths";

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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [tab, setTab] = useState<"about" | "conversation">("about");

  return (
    <div className="w-full text-left">
      {showPageHeader ? (
        <B2CPageHeader
          title="Slides"
          subtitle="Video presentations by topic"
          back={
            showBackLink
              ? { href: hrefFor(studyListPath("slide_deck")), label: STUDY_KIND_LABEL.slide_deck }
              : undefined
          }
        />
      ) : null}

      <div className={cn("flex flex-col gap-4 lg:flex-row lg:items-start", !showPageHeader && "mt-0")}>
        {!sidebarOpen && (
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className={cn(t.b2cGhostButton, "w-full justify-start lg:hidden")}
            aria-label="Open presentations list"
          >
            <HiOutlineBars3 className="h-4 w-4 shrink-0 text-osce-accent" aria-hidden />
            <span className="truncate">{selected.title}</span>
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

            <DeckList
              items={decks}
              currentSlug={selected.slug}
              deckHref={deckHref}
              onPick={() => setSidebarOpen(false)}
              specialty={specialty}
              onSpecialtyChange={onSpecialtyChange}
              specialtyOptions={specialtyOptions}
              hasUncategorized={hasUncategorized}
            />
          </B2CPanelCard>
        </aside>

        <B2CPanelCard className="mt-0 flex min-w-0 flex-1 flex-col">
          <B2CPanelCardHeader className="truncate">{selected.title}</B2CPanelCardHeader>

          <div className="flex min-h-[280px] items-center justify-center bg-osce-surface p-4 sm:p-6 lg:min-h-[360px]">
            <DeckStage item={selected} />
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
                  ? (aboutText(selected) ?? "No description.")
                  : "No conversation available for this presentation."}
              </p>
            </div>
          </div>
        </B2CPanelCard>
      </div>
    </div>
  );
}
