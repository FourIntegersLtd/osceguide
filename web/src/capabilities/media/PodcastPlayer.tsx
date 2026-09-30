"use client";

import { useEffect, useRef, useState } from "react";
import {
  HiOutlineChevronDown,
  HiOutlineChevronLeft,
  HiOutlineChevronRight,
  HiOutlineListBullet,
  HiOutlinePause,
  HiOutlinePlay,
} from "react-icons/hi2";
import { LuPodcast } from "react-icons/lu";
import { recordActivity } from "@/capabilities/account/api";
import { DiscussWithAthena } from "@/capabilities/help/DiscussWithAthena";
import {
  ModalContent,
  ModalFooterActions,
  ModalFootnote,
  ModalLead,
  ModalPrimaryButton,
  ModalSecondaryButton,
  ModalSection,
  cn,
} from "@/foundation/ui";

export interface Episode {
  id: string;
  /**
   * What the tutor's notes and a suggestion address the episode by. Only a
   * podcast episode has one; a summary's audio is not a listen to record.
   */
  slug?: string;
  title: string;
  url: string | null;
}

/**
 * The episode player, with the rest of the series under it.
 *
 * Unchanged in behaviour from the retiring client's podcast modal — autoplay
 * on to the next episode, the collapsible playlist, the AI-pronunciation
 * footnote — but it is given its episodes rather than fetching them, because
 * it is now used in two places: the modal on a summary and the episode page
 * the `podcast` kind gets of its own.
 */
export function PodcastPlayer({
  episodes,
  index,
  onIndexChange,
  heading = "lead",
}: {
  episodes: Episode[];
  index: number;
  onIndexChange: (next: number) => void;
  /** `meta` when the page already carries the episode's title above it. */
  heading?: "lead" | "meta";
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showPlaylist, setShowPlaylist] = useState(false);
  // Episodes already told to the tutor while this player is open; pausing and
  // playing again is one listen, not two.
  const listenedTo = useRef(new Set<string>());

  const current = episodes[index];
  const hasPlaylist = episodes.length > 1;
  const canGoNext = index < episodes.length - 1;
  const canGoPrevious = index > 0;
  const byline = `with Ben & Michelle${
    hasPlaylist ? ` · Episode ${index + 1} of ${episodes.length}` : ""
  } · 7–10 min`;

  /**
   * The old player reloaded the element behind a 100ms `setTimeout`, which is
   * a race it usually won. Changing the `src` is what needs the reload, so it
   * happens when the element reports the new source can play.
   */
  const go = (next: number, autoplay = false) => {
    if (next < 0 || next >= episodes.length) return;
    onIndexChange(next);
    if (autoplay) setIsPlaying(true);
  };

  useEffect(() => {
    if (!isPlaying || !audioRef.current?.src) return;
    const element = audioRef.current;
    void element.play().catch(() => setIsPlaying(false));
  }, [index, isPlaying]);

  return (
    <ModalContent>
      {heading === "lead" ? (
        <ModalLead
          eyebrow="Podcast"
          title={current?.title ?? "Episode"}
          description={byline}
          icon={<LuPodcast className="h-5 w-5" />}
        />
      ) : (
        <p className="inline-flex items-center gap-2 text-osce-meta text-b2c-text-muted">
          <LuPodcast className="h-4 w-4 text-osce-accent" aria-hidden />
          {byline}
        </p>
      )}

      {current?.slug ? (
        <div>
          <DiscussWithAthena topic={{ title: current.title, kind: "podcast", slug: current.slug }} />
        </div>
      ) : null}

      <ModalSection>
        {current?.url ? (
          // Episodes have no transcript to attach yet; the accessibility
          // statement lists this as a known gap.
          // eslint-disable-next-line jsx-a11y/media-has-caption
          <audio
            ref={audioRef}
            key={current.url}
            src={current.url}
            autoPlay={isPlaying}
            onEnded={() => {
              if (canGoNext) go(index + 1, true);
              else setIsPlaying(false);
            }}
            onPlay={() => {
              setIsPlaying(true);
              const slug = current?.slug;
              if (current && slug && !listenedTo.current.has(slug)) {
                listenedTo.current.add(slug);
                void recordActivity({ kind: "listened", ref_kind: "podcast", ref_id: slug, title: current.title });
              }
            }}
            onPause={() => setIsPlaying(false)}
            className="w-full"
            controls
            controlsList="nodownload"
          />
        ) : (
          <p className="text-osce-body text-b2c-text-secondary">
            This episode has no audio attached yet.
          </p>
        )}
      </ModalSection>

      <ModalFootnote>
        <span className="font-medium text-osce-ink-900">AI-generated:</span> Some medical terms may
        have unusual pronunciations.
      </ModalFootnote>

      {hasPlaylist ? (
        <>
          <ModalFooterActions>
            <ModalSecondaryButton
              type="button"
              onClick={() => go(index - 1)}
              disabled={!canGoPrevious}
              className="gap-1.5"
            >
              <HiOutlineChevronLeft className="h-3.5 w-3.5" aria-hidden />
              Previous
            </ModalSecondaryButton>
            <ModalPrimaryButton
              type="button"
              onClick={() => go(index + 1)}
              disabled={!canGoNext}
              className="gap-1.5"
            >
              Next
              <HiOutlineChevronRight className="h-3.5 w-3.5" aria-hidden />
            </ModalPrimaryButton>
          </ModalFooterActions>

          <ModalSection bodyClassName="overflow-hidden px-0 py-0 sm:px-0 sm:py-0">
            <button
              type="button"
              onClick={() => setShowPlaylist(!showPlaylist)}
              className="flex w-full items-center justify-between border-b border-b2c-border bg-b2c-surface-muted px-4 py-3 text-left text-osce-body font-medium text-b2c-text-secondary transition hover:bg-b2c-secondary"
            >
              <span className="inline-flex items-center gap-2">
                <HiOutlineListBullet className="h-3.5 w-3.5 text-osce-accent" aria-hidden />
                Playlist ({episodes.length} episodes)
              </span>
              <HiOutlineChevronDown
                className={cn(
                  "h-3.5 w-3.5 text-b2c-text-muted transition-transform",
                  showPlaylist && "rotate-180",
                )}
                aria-hidden
              />
            </button>
            {showPlaylist ? (
              <ul>
                {episodes.map((episode, position) => (
                  <li key={episode.id} className="border-b border-b2c-border last:border-b-0">
                    <button
                      type="button"
                      onClick={() => {
                        go(position);
                        setShowPlaylist(false);
                      }}
                      className={cn(
                        "flex w-full items-center gap-3 px-4 py-3 text-left transition hover:bg-b2c-surface-muted",
                        position === index && "bg-b2c-surface-muted",
                      )}
                    >
                      <span
                        className={cn(
                          "flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-osce-meta font-medium",
                          position === index
                            ? "bg-osce-accent text-white"
                            : "bg-b2c-secondary text-b2c-text-secondary",
                        )}
                      >
                        {position + 1}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-osce-body font-medium text-osce-ink-900">
                          {episode.title}
                        </span>
                        <span className="mt-0.5 block text-osce-meta text-b2c-text-muted">
                          7–10 min · with Ben &amp; Michelle
                        </span>
                      </span>
                      {position === index ? (
                        <span className="inline-flex items-center gap-1 text-osce-meta font-medium text-osce-accent">
                          {isPlaying ? (
                            <HiOutlinePause className="h-3 w-3" aria-hidden />
                          ) : (
                            <HiOutlinePlay className="h-3 w-3" aria-hidden />
                          )}
                          Now playing
                        </span>
                      ) : null}
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </ModalSection>
        </>
      ) : null}
    </ModalContent>
  );
}
