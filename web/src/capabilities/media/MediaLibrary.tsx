"use client";

import Link from "next/link";
import { useState } from "react";
import { LuFileText, LuHeadphones, LuNewspaper, LuPresentation } from "react-icons/lu";
import { AsyncBoundary, Badge, PageHeader, cn } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import {
  MEDIA_KINDS,
  MEDIA_KIND_LABELS,
  listMedia,
  type MediaItem,
  type MediaKind,
} from "@/capabilities/media/api";

const KIND_ICON: Record<MediaKind, typeof LuPresentation> = {
  slide: LuPresentation,
  summary: LuFileText,
  blog: LuNewspaper,
  podcast: LuHeadphones,
};

/**
 * The study library.
 *
 * Mounted on Train and Assess from the same file. It asks the surface only for
 * its own base path, so an institution's trainees get the decks and summaries
 * their programme publishes without a line of institution-specific code here.
 */
export function MediaLibrary({ initialKind = null }: { initialKind?: MediaKind | null }) {
  const [kind, setKind] = useState<MediaKind | null>(initialKind);
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => listMedia({ kind, limit: 60 }, signal), [kind]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Study material"
        description="Decks, summaries, articles and episodes published for your exams."
      />

      <div className="flex flex-wrap gap-2" role="tablist" aria-label="Material type">
        <FilterChip active={kind === null} onClick={() => setKind(null)}>
          Everything
        </FilterChip>
        {MEDIA_KINDS.map((option) => (
          <FilterChip key={option} active={kind === option} onClick={() => setKind(option)}>
            {MEDIA_KIND_LABELS[option].many}
          </FilterChip>
        ))}
      </div>

      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{
          title: "Nothing published yet",
          description:
            kind === null
              ? "Study material appears here as it is published for your exams."
              : `No ${MEDIA_KIND_LABELS[kind].many.toLowerCase()} have been published yet.`,
        }}
      >
        {(page) => (
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {page.items.map((item) => (
              <li key={item.id}>
                <MediaCard item={item} href={hrefFor(`/library/${item.slug}`)} />
              </li>
            ))}
          </ul>
        )}
      </AsyncBoundary>
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        "rounded-full border px-3 py-1.5 text-sm font-medium transition-colors",
        active
          ? "border-accent bg-accent text-ink-inverse"
          : "border-border bg-surface text-ink-muted hover:border-border-strong hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}

function MediaCard({ item, href }: { item: MediaItem; href: string }) {
  const kind = (MEDIA_KINDS as readonly string[]).includes(item.kind)
    ? (item.kind as MediaKind)
    : null;
  const Icon = kind ? KIND_ICON[kind] : LuFileText;

  return (
    <Link
      href={href}
      className="group flex h-full flex-col gap-3 rounded-panel border border-border bg-surface p-4 transition-colors hover:border-border-strong"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-2 text-xs font-medium text-ink-muted">
          <Icon className="h-4 w-4" aria-hidden />
          {kind ? MEDIA_KIND_LABELS[kind].one : item.kind}
        </span>
        {item.exam_code && <Badge tone="accent">{item.exam_code.toUpperCase()}</Badge>}
      </div>
      <h3 className="text-sm font-semibold text-ink group-hover:text-accent">{item.title}</h3>
      {item.summary && <p className="line-clamp-3 text-sm text-ink-muted">{item.summary}</p>}
    </Link>
  );
}
