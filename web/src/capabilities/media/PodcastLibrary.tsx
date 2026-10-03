"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { HiOutlinePlay } from "react-icons/hi2";
import { LuHeadphones } from "react-icons/lu";
import { B2CEmptyState, productTokens as t } from "@/foundation/ui";
import { useSurface } from "@/capabilities/SurfaceContext";
import {
  audioUrl,
  bodyMarkdown,
  readMedia,
  podcastGroupLabel,
  podcastSeries,
  type MediaItem,
} from "@/capabilities/media/api";
import { useCurrentExam } from "@/foundation/session";
import { useAsync } from "@/foundation/hooks";
import { DiscussWithAthena } from "@/capabilities/help/DiscussWithAthena";
import { EpisodePanel } from "@/capabilities/media/EpisodePanel";
import { Prose } from "@/capabilities/media/Prose";
import { podcastEpisodePath } from "@/capabilities/media/studyPaths";
import type { Episode } from "@/capabilities/media/PodcastPlayer";
import { B2CGroupedRowLink, B2CGroupedSection } from "@/foundation/ui/B2CGroupedList";

function resolveSelected(
  episodes: MediaItem[],
  episodeParam: string | null,
  fetched: MediaItem | null,
): MediaItem | null {
  if (episodes.length === 0) return null;
  if (episodeParam) {
    const match = episodes.find((entry) => entry.slug === episodeParam);
    if (match) return match;
    if (fetched?.slug === episodeParam) return fetched;
  }
  return episodes[0] ?? null;
}

function publishedSortKey(item: MediaItem): number {
  if (!item.published_at) return 0;
  const ms = Date.parse(item.published_at);
  return Number.isFinite(ms) ? ms : 0;
}

function groupPodcasts(items: MediaItem[]): { label: string; episodes: MediaItem[] }[] {
  const map = new Map<string, MediaItem[]>();
  for (const item of items) {
    const label = podcastGroupLabel(item);
    const list = map.get(label) ?? [];
    list.push(item);
    map.set(label, list);
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([label, episodes]) => ({
      label,
      episodes: [...episodes].sort((a, b) => publishedSortKey(b) - publishedSortKey(a)),
    }));
}

function PodcastLibraryBody({
  items,
  allItemsCount,
}: {
  items: MediaItem[];
  allItemsCount: number;
}) {
  const { hrefFor } = useSurface();
  const { code: examCode } = useCurrentExam();
  const router = useRouter();
  const searchParams = useSearchParams();
  const episodeParam = searchParams.get("episode");
  const [indexOverride, setIndexOverride] = useState<number | null>(null);

  // The list is one page of the catalogue, so an episode found by search can
  // be beyond it; it is read by slug rather than silently swapped for the first.
  const listed = episodeParam !== null && items.some((entry) => entry.slug === episodeParam);
  const fetchedState = useAsync(
    (signal) => (episodeParam && !listed ? readMedia(episodeParam, signal) : Promise.resolve(null)),
    [episodeParam, listed],
  );
  const selected = resolveSelected(items, episodeParam, fetchedState.data ?? null);
  const episodeHref = (slug: string) => hrefFor(podcastEpisodePath(slug));

  useEffect(() => {
    setIndexOverride(null);
  }, [episodeParam]);

  if (items.length === 0) {
    return (
      <B2CEmptyState
        icon={LuHeadphones}
        title="No episodes yet"
        description={
          allItemsCount > 0 && examCode
            ? `Nothing published for ${examCode.toUpperCase()} yet. Switch exam in the menu or upgrade for full access.`
            : "Episodes appear here as they are published."
        }
      />
    );
  }

  if (!selected) return null;

  const series = podcastSeries(items, selected, examCode);
  const fallbackIndex = Math.max(0, series.findIndex((entry) => entry.id === selected.id));
  const currentIndex = indexOverride ?? fallbackIndex;
  const current = series[currentIndex] ?? selected;
  const playerEpisodes: Episode[] = series.map((entry) => ({
    id: entry.id,
    slug: entry.slug,
    title: entry.title,
    url: audioUrl(entry),
  }));

  const onIndexChange = (next: number) => {
    setIndexOverride(next);
    const entry = series[next];
    if (entry) {
      router.replace(episodeHref(entry.slug), { scroll: false });
    }
  };

  const groups = groupPodcasts(items);
  const notes = bodyMarkdown(current);

  return (
    <div className="space-y-6">
      <EpisodePanel episodes={playerEpisodes} index={currentIndex} onIndexChange={onIndexChange} current={current} />

      {groups.map((group) => (
        <B2CGroupedSection key={group.label} eyebrow={groups.length > 1 ? group.label : "Episodes"}>
          {group.episodes.map((episode) => {
            const active = episode.slug === current.slug;
            return (
              <B2CGroupedRowLink
                key={episode.id}
                href={episodeHref(episode.slug)}
                scroll={false}
                icon={HiOutlinePlay}
                title={episode.title}
                meta={audioUrl(episode) !== null ? "Ready to play" : "Audio not available"}
                trailing={
                  active ? (
                    <span className="inline-flex h-[22px] shrink-0 items-center gap-1.5 whitespace-nowrap rounded-osce-sm bg-b2c-surface-muted px-2 text-osce-caption font-medium text-osce-ink-900">
                      <span className="h-1.5 w-1.5 rounded-full bg-osce-accent" aria-hidden />
                      Now playing
                    </span>
                  ) : null
                }
              />
            );
          })}
        </B2CGroupedSection>
      ))}

      <DiscussWithAthena topic={{ title: current.title, kind: "podcast", slug: current.slug }} />
      {notes ? (
        <div className={t.b2cProseMeasureWide}>
          <Prose content={notes} />
        </div>
      ) : null}
    </div>
  );
}

export function PodcastLibrary({
  items,
  allItemsCount,
}: {
  items: MediaItem[];
  allItemsCount: number;
}) {
  return (
    <Suspense fallback={null}>
      <PodcastLibraryBody items={items} allItemsCount={allItemsCount} />
    </Suspense>
  );
}
