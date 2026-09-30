"use client";

import { B2CPanelCard, B2CPanelCardBody, cn, productTokens as t } from "@/foundation/ui";
import { bodyMarkdown, type MediaItem } from "@/capabilities/media/api";
import { PodcastPlayer, type Episode } from "@/capabilities/media/PodcastPlayer";
import { Prose } from "@/capabilities/media/Prose";

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
    <div className={cn("min-w-0 space-y-6", t.b2cProseMeasureWide)}>
      <B2CPanelCard className="mt-0 overflow-hidden bg-gradient-to-br from-b2c-surface-muted via-osce-surface to-b2c-surface-muted">
        <B2CPanelCardBody className="p-5 sm:p-8">
          <p className={cn(t.b2cEyebrow, "text-osce-accent")}>Now playing</p>
          <h2 className={cn("mt-2 text-balance", t.b2cPageTitle)}>{current.title}</h2>
          {current.summary ? (
            <p className={cn("mt-2 line-clamp-2", t.b2cBodyTextMuted)}>{current.summary}</p>
          ) : null}
          <div className="mt-6">
            <PodcastPlayer
              episodes={episodes}
              index={index}
              onIndexChange={onIndexChange}
              heading="meta"
            />
          </div>
        </B2CPanelCardBody>
      </B2CPanelCard>

      {notes ? <Prose content={notes} /> : null}
    </div>
  );
}
