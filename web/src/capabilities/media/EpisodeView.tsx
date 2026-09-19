"use client";

import { useState } from "react";
import {
  AsyncBoundary,
  B2CPageHeader,
  B2CPanelCard,
  B2CPanelCardBody,
  cn,
  productTokens as t,
} from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { audioUrl, bodyMarkdown, listAllMedia, type MediaItem } from "@/capabilities/media/api";
import { PodcastPlayer, type Episode } from "@/capabilities/media/PodcastPlayer";
import { Prose } from "@/capabilities/media/Prose";

/**
 * A podcast episode.
 *
 * On the retiring client an episode had no page: it was audio hanging off a
 * summary, reachable only through a modal on that summary. A `podcast` row is
 * study material in its own right here, so it has an address, a description
 * and the series beside it — and the player itself is the same component the
 * summary's modal uses.
 */
export function EpisodeView({
  item,
  hrefFor,
}: {
  item: MediaItem;
  hrefFor: (path: string) => string;
}) {
  const state = useAsync((signal) => listAllMedia("podcast", signal), []);
  const [index, setIndex] = useState<number | null>(null);
  const notes = bodyMarkdown(item);

  return (
    <div className="w-full text-left">
      <B2CPageHeader
        title={item.title}
        subtitle={item.summary ?? undefined}
        back={{ href: hrefFor("/library"), label: "Study material" }}
      />

      <div className={cn("mt-6 space-y-6", t.b2cProseMeasureWide)}>
        <B2CPanelCard className="mt-0">
          <B2CPanelCardBody>
            <AsyncBoundary state={state}>
              {(items) => {
                const series = items.length > 0 ? items : [item];
                const episodes: Episode[] = series.map((entry) => ({
                  id: entry.id,
                  title: entry.title,
                  url: audioUrl(entry),
                }));
                const fallback = Math.max(
                  0,
                  episodes.findIndex((entry) => entry.id === item.id),
                );
                return (
                  <PodcastPlayer
                    episodes={episodes}
                    index={index ?? fallback}
                    onIndexChange={setIndex}
                    heading="meta"
                  />
                );
              }}
            </AsyncBoundary>
          </B2CPanelCardBody>
        </B2CPanelCard>

        {notes ? <Prose content={notes} /> : null}
      </div>
    </div>
  );
}
