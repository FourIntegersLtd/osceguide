"use client";

import { useState } from "react";
import {
  AsyncBoundary,
  B2CPageHeader,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useCurrentExam } from "@/foundation/session";
import {
  audioUrl,
  listAllMedia,
  podcastSeries,
  type MediaItem,
} from "@/capabilities/media/api";
import { STUDY_KIND_LABEL, studyListPath } from "@/capabilities/media/studyPaths";
import { EpisodePanel } from "@/capabilities/media/EpisodePanel";
import type { Episode } from "@/capabilities/media/PodcastPlayer";

/**
 * A podcast episode (legacy `/library` path redirects to `/podcast?episode=`).
 */
export function EpisodeView({
  item,
  hrefFor,
}: {
  item: MediaItem;
  hrefFor: (path: string) => string;
}) {
  const { code: examCode } = useCurrentExam();
  const state = useAsync((signal) => listAllMedia("podcast", signal), []);
  const [index, setIndex] = useState<number | null>(null);

  return (
    <div className="w-full text-left">
      <AsyncBoundary state={state}>
        {(items) => {
          const series = podcastSeries(items, item, examCode);
          const fallback = Math.max(
            0,
            series.findIndex((entry) => entry.id === item.id),
          );
          const currentIndex = index ?? fallback;
          const current = series[currentIndex] ?? item;
          const episodes: Episode[] = series.map((entry) => ({
            id: entry.id,
            title: entry.title,
            url: audioUrl(entry),
          }));

          return (
            <>
              <B2CPageHeader
                title={current.title}
                subtitle={current.summary ?? undefined}
                back={{ href: hrefFor(studyListPath("podcast")), label: STUDY_KIND_LABEL.podcast }}
              />

              <div className={cn("mt-6", t.b2cProseMeasureWide)}>
                <EpisodePanel
                  episodes={episodes}
                  index={currentIndex}
                  onIndexChange={setIndex}
                  current={current}
                />
              </div>
            </>
          );
        }}
      </AsyncBoundary>
    </div>
  );
}
