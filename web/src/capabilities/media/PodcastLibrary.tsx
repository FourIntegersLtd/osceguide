"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { HiOutlineBars3, HiOutlinePlay, HiOutlineXMark } from "react-icons/hi2";
import { LuHeadphones } from "react-icons/lu";
import {
  B2CEmptyState,
  B2CPanelCard,
  B2CPanelCardHeader,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import { useSurface } from "@/capabilities/SurfaceContext";
import {
  audioUrl,
  podcastGroupLabel,
  podcastSeries,
  type MediaItem,
} from "@/capabilities/media/api";
import { useCurrentExam } from "@/foundation/session";
import { EpisodePanel } from "@/capabilities/media/EpisodePanel";
import { podcastEpisodePath } from "@/capabilities/media/studyPaths";
import type { Episode } from "@/capabilities/media/PodcastPlayer";

function resolveSelected(episodes: MediaItem[], episodeParam: string | null): MediaItem | null {
  if (episodes.length === 0) return null;
  if (episodeParam) {
    const match = episodes.find((entry) => entry.slug === episodeParam);
    if (match) return match;
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [indexOverride, setIndexOverride] = useState<number | null>(null);

  const selected = resolveSelected(items, episodeParam);
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

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
      {!sidebarOpen && (
        <button
          type="button"
          onClick={() => setSidebarOpen(true)}
          className={cn(t.b2cGhostButton, "w-full justify-start lg:hidden")}
          aria-label="Open episode list"
        >
          <HiOutlineBars3 className="h-4 w-4 shrink-0 text-osce-accent" aria-hidden />
          <span className="truncate">{current.title}</span>
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
            <span>Episodes</span>
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              className={cn(t.b2cIconButton, "lg:hidden")}
              aria-label="Close episode list"
            >
              <HiOutlineXMark className="h-5 w-5" aria-hidden />
            </button>
          </B2CPanelCardHeader>

          <div className={cn("min-h-0 flex-1", t.b2cScrollY)}>
            {groups.map((group) => (
              <div key={group.label} className="border-b border-b2c-border last:border-b-0">
                <p className={cn(t.b2cFieldLabel, "px-4 pb-2 pt-4 sm:px-5")}>{group.label}</p>
                {group.episodes.map((episode) => {
                  const active = episode.slug === current.slug;
                  const hasAudio = audioUrl(episode) !== null;
                  return (
                    <Link
                      key={episode.id}
                      href={episodeHref(episode.slug)}
                      scroll={false}
                      onClick={() => setSidebarOpen(false)}
                      aria-current={active ? "page" : undefined}
                      className={cn(
                        "flex w-full items-start gap-3 border-l-2 px-4 py-3.5 text-left transition-colors sm:px-5",
                        active
                          ? "border-l-b2c-primary bg-b2c-surface-muted"
                          : "border-l-transparent hover:bg-b2c-surface-muted",
                      )}
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
                          active ? "bg-osce-accent text-white" : "bg-b2c-surface-muted text-osce-accent",
                        )}
                        aria-hidden
                      >
                        <HiOutlinePlay className="h-4 w-4" />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className={cn(t.b2cPanelListRowTitle, "line-clamp-2", active && "text-osce-accent")}>
                          {episode.title}
                        </span>
                        <span className={cn(t.b2cPanelCardMeta, "mt-0.5 block")}>
                          {hasAudio ? "Ready to play" : "Audio not available"}
                        </span>
                      </span>
                    </Link>
                  );
                })}
              </div>
            ))}
          </div>
        </B2CPanelCard>
      </aside>

      <div className="min-w-0 flex-1">
        <EpisodePanel
          episodes={playerEpisodes}
          index={currentIndex}
          onIndexChange={onIndexChange}
          current={current}
        />
      </div>
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
