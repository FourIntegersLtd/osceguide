"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { HiOutlineArrowRight } from "react-icons/hi2";
import { LuStethoscope } from "react-icons/lu";
import {
  B2CEmptyState,
  B2CPanelCard,
  B2CPanelCardHeader,
  B2CSegmentedTabs,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import { specialtiesOf, type MediaItem } from "@/capabilities/media/api";

type SummaryView = "az" | "specialty";

/**
 * The A-to-Z.
 *
 * The retiring client kept the open letter in the URL and pushed a new one on
 * every click, so browsing the index filled the back stack with letters. It is
 * component state here: the address of a summary is the summary's own page,
 * which is the thing worth linking to.
 */
export function SummaryIndex({
  items,
  hrefFor,
}: {
  items: MediaItem[];
  hrefFor: (path: string) => string;
}) {
  const [view, setView] = useState<SummaryView>("az");
  const [open, setOpen] = useState<string | null>(null);

  const groups = view === "az" ? groupByLetter(items) : groupBySpecialty(items);
  const keys = Object.keys(groups).sort();

  const switchView = (next: SummaryView) => {
    setView(next);
    setOpen(null);
  };

  return (
    <div className="space-y-8 text-left">
      <B2CSegmentedTabs
        items={[
          { id: "az", label: "A to Z" },
          { id: "specialty", label: "Specialty" },
        ]}
        value={view}
        onChange={switchView}
        aria-label="Summary view"
      />

      {keys.length === 0 && view === "specialty" ? (
        <B2CEmptyState
          icon={LuStethoscope}
          title="Nothing is filed under a specialty yet"
          description="Summaries appear here once they are published with one."
        />
      ) : null}

      <div className="lg:flex lg:items-start lg:gap-10">
        {view === "az" && keys.length > 0 ? (
          <nav
            aria-label="Jump to letter"
            className={cn(
              "mb-2 hidden shrink-0 lg:sticky lg:top-24 lg:block lg:w-10",
              t.b2cScrollY,
              "lg:max-h-[min(70vh,28rem)]",
            )}
          >
            <ul className="flex flex-col gap-0.5">
              {keys.map((key) => {
                const selected = open === key;
                return (
                  <li key={key}>
                    <button
                      type="button"
                      onClick={() => setOpen(selected ? null : key)}
                      className={cn(
                        "flex h-8 w-8 items-center justify-center rounded-md text-sm font-medium transition-colors",
                        selected
                          ? "bg-osce-accent text-white"
                          : "text-osce-ink-500 hover:bg-b2c-surface-muted hover:text-osce-ink-900",
                      )}
                      aria-pressed={selected}
                    >
                      {key}
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
        ) : null}

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap gap-3 sm:gap-4">
            {keys.map((key) => {
              const selected = open === key;
              const count = groups[key]?.length ?? 0;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setOpen(selected ? null : key)}
                  className={cn(
                    view === "az" ? t.b2cPickerChipLetter : t.b2cPickerChipSpecialty,
                    selected && t.b2cPickerChipSelected,
                  )}
                  aria-pressed={selected}
                  aria-label={
                    view === "az"
                      ? `Letter ${key}, ${count} topics`
                      : `${key}, ${count} topics`
                  }
                >
                  {key}
                </button>
              );
            })}
          </div>

          {open && groups[open] ? (
            <OpenGroup heading={open} items={groups[open]} hrefFor={hrefFor} />
          ) : null}
        </div>
      </div>
    </div>
  );
}

function OpenGroup({
  heading,
  items,
  hrefFor,
}: {
  heading: string;
  items: MediaItem[];
  hrefFor: (path: string) => string;
}) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [heading]);

  return (
    <div ref={ref} className="scroll-mt-20 lg:scroll-mt-8">
      <B2CPanelCard className="mt-0">
        <B2CPanelCardHeader>
          <span>{heading}</span>
          <span className={t.b2cPanelCardMeta}>{items.length} topics</span>
        </B2CPanelCardHeader>
        <ul>
          {items.map((item) => (
            <li key={item.id}>
              <Link href={hrefFor(`/library/${item.slug}`)} className={t.b2cPanelListRow}>
                <span className={t.b2cPanelListRowTitle}>{item.title}</span>
                <HiOutlineArrowRight
                  className="h-3.5 w-3.5 shrink-0 text-b2c-text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-osce-accent"
                  aria-hidden
                />
              </Link>
            </li>
          ))}
        </ul>
      </B2CPanelCard>
    </div>
  );
}

function groupByLetter(items: MediaItem[]): Record<string, MediaItem[]> {
  return items.reduce<Record<string, MediaItem[]>>((acc, item) => {
    const letter = item.title.charAt(0).toUpperCase();
    (acc[letter] ??= []).push(item);
    return acc;
  }, {});
}

/**
 * An item with several specialties appears under each of them, as it did
 * before. Items with none are left out entirely rather than gathered under
 * "Unknown": on this backend that is every item, and a single bucket holding
 * the whole library is worse than an empty state that says so.
 */
function groupBySpecialty(items: MediaItem[]): Record<string, MediaItem[]> {
  return items.reduce<Record<string, MediaItem[]>>((acc, item) => {
    for (const specialty of specialtiesOf(item)) {
      (acc[specialty] ??= []).push(item);
    }
    return acc;
  }, {});
}
