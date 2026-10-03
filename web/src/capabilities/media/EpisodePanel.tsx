"use client";

import { productTokens as t } from "@/foundation/ui";
import { bodyMarkdown, type MediaItem } from "@/capabilities/media/api";
import { PodcastPlayer, type Episode } from "@/capabilities/media/PodcastPlayer";
import { Prose } from "@/capabilities/media/Prose";
import { B2CHero } from "@/foundation/ui/B2CHero";

export function EpisodePanel({
  episodes,
  index,
  onIndexChange,
  current,
}: {
  episodes: Episode[];
  index: number;
  onIndexChange: (index: number) => void;
  current: MediaItem;
}) {
  const notes = bodyMarkdown(current);

  return (
    <div className="min-w-0 space-y-6">
      <B2CHero
        eyebrow="Now playing"
        title={current.title}
        action={
          <div className="w-full">
            <PodcastPlayer episodes={episodes} index={index} onIndexChange={onIndexChange} heading="meta" />
          </div>
        }
      >
        {current.summary ? <span className="line-clamp-2">{current.summary}</span> : null}
      </B2CHero>

      {notes ? (
        <div className={t.b2cProseMeasureWide}>
          <Prose content={notes} />
        </div>
      ) : null}
    </div>
  );
}
