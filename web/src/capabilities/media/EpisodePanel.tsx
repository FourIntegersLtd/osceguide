"use client";

import { PODCAST_LENGTH_LABEL } from "@/capabilities/media/limits";
import { useEffect, useRef, useState } from "react";
import { HiOutlineChevronLeft, HiOutlinePause, HiOutlinePlay } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { B2CHero } from "@/foundation/ui/B2CHero";
import { recordActivity } from "@/capabilities/account/api";
import type { MediaItem } from "@/capabilities/media/api";
import type { Episode } from "@/capabilities/media/PodcastPlayer";
import { clockTime } from "@/capabilities/media/support/text";

/**
 * The episode page's player (canvas `train-podcast`): the title and its
 * controls in the hero, the progress beside them.
 *
 * It behaves as the summary modal's `PodcastPlayer` does: the next episode
 * starts when one ends, and a listen is told to the tutor once per episode.
 * The audio element is hidden and these controls drive it; the track is a
 * slider, so the keyboard can seek as well. The episode's notes sit under the
 * list of episodes, in `PodcastLibrary`.
 */
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
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  // True from asking for audio until the element reports it is playing.
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState({ url: "", position: 0, duration: 0 });
  // Episodes already told to the tutor while this page is open; pausing and
  // playing again is one listen, not two.
  const listenedTo = useRef(new Set<string>());

  const episode = episodes[index];
  const url = episode?.url ?? null;
  const canGoNext = index < episodes.length - 1;
  const canGoPrevious = index > 0;
  // Progress belongs to one episode's audio; a new episode starts from nothing.
  const position = progress.url === url ? progress.position : 0;
  const duration = progress.url === url ? progress.duration : 0;

  const go = (next: number, autoplay = false) => {
    if (next < 0 || next >= episodes.length) return;
    onIndexChange(next);
    if (autoplay) setIsPlaying(true);
  };

  // Choosing another episode (its row in the list, Previous, Next) starts it:
  // the page's first episode stays silent until Play, but a later change of
  // source is always the listener asking to hear it.
  const [lastUrl, setLastUrl] = useState(url);
  if (url !== lastUrl) {
    setLastUrl(url);
    if (url) {
      setIsPlaying(true);
      setLoading(true);
    }
  }

  // Changing episode swaps the element (it is keyed by its source), so a
  // player that was playing starts the new one.
  useEffect(() => {
    if (!isPlaying || !audioRef.current?.src) return;
    void audioRef.current.play().catch(() => setIsPlaying(false));
  }, [index, isPlaying]);

  const toggle = () => {
    const element = audioRef.current;
    if (!element) return;
    if (element.paused) {
      setLoading(true);
      void element.play().catch(() => {
        setIsPlaying(false);
        setLoading(false);
      });
    } else element.pause();
  };

  const read = (element: HTMLAudioElement) => {
    setProgress({
      url: url ?? "",
      position: element.currentTime,
      duration: Number.isFinite(element.duration) ? element.duration : 0,
    });
  };

  return (
    <div className="min-w-0">
      <B2CHero
        eyebrow="Now playing"
        title={current.title}
        action={
          <>
            <Button onClick={toggle} disabled={!url} aria-busy={loading} className="gap-2">
              {loading ? (
                <span
                  className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent"
                  aria-hidden
                />
              ) : isPlaying ? (
                <HiOutlinePause className="h-4 w-4" aria-hidden />
              ) : (
                <HiOutlinePlay className="h-4 w-4" aria-hidden />
              )}
              {loading ? "Loading…" : isPlaying ? "Pause" : "Play"}
            </Button>
            <Button variant="secondary" onClick={() => go(index - 1)} disabled={!canGoPrevious} className="gap-1.5">
              <HiOutlineChevronLeft className="h-4 w-4" aria-hidden />
              Previous
            </Button>
            <Button variant="secondary" onClick={() => go(index + 1)} disabled={!canGoNext}>
              Next
            </Button>
          </>
        }
        aside={
          <div className="w-full self-center sm:w-[300px]">
            <input
              type="range"
              min={0}
              max={duration || 1}
              step={1}
              value={Math.min(position, duration || 1)}
              disabled={!url || duration === 0}
              onChange={(event) => {
                const element = audioRef.current;
                if (!element) return;
                element.currentTime = Number(event.target.value);
                read(element);
              }}
              aria-label="Position in the episode"
              aria-valuetext={`${clockTime(position)} of ${clockTime(duration)}`}
              className="block h-1.5 w-full cursor-pointer appearance-none rounded-osce-md bg-osce-border disabled:cursor-default [&::-moz-range-thumb]:h-0 [&::-moz-range-thumb]:w-0 [&::-moz-range-thumb]:border-0 [&::-webkit-slider-thumb]:h-0 [&::-webkit-slider-thumb]:w-0 [&::-webkit-slider-thumb]:appearance-none"
              style={{
                // The played part, painted on the track itself.
                backgroundImage:
                  "linear-gradient(var(--osce-tone-education-text), var(--osce-tone-education-text))",
                backgroundRepeat: "no-repeat",
                backgroundSize: `${duration > 0 ? (position / duration) * 100 : 0}% 100%`,
              }}
            />
            <p className="mt-2 font-mono text-osce-meta tabular-nums text-b2c-text-muted">
              {clockTime(position)} / {clockTime(duration)}
            </p>
          </div>
        }
      >
        {url
          ? `${PODCAST_LENGTH_LABEL} · with Ben & Michelle. AI-generated: some medical terms may be mispronounced.`
          : "This episode has no audio attached yet."}
      </B2CHero>

      {url ? (
        // Episodes have no transcript to attach yet; the accessibility
        // statement lists this as a known gap.
        // eslint-disable-next-line jsx-a11y/media-has-caption
        <audio
          ref={audioRef}
          key={url}
          src={url}
          autoPlay={isPlaying}
          preload="metadata"
          onLoadedMetadata={(event) => read(event.currentTarget)}
          onTimeUpdate={(event) => read(event.currentTarget)}
          onEnded={() => {
            if (canGoNext) go(index + 1, true);
            else setIsPlaying(false);
          }}
          onPlay={() => {
            setIsPlaying(true);
            const slug = episode?.slug;
            if (episode && slug && !listenedTo.current.has(slug)) {
              listenedTo.current.add(slug);
              void recordActivity({ kind: "listened", ref_kind: "podcast", ref_id: slug, title: episode.title });
            }
          }}
          onPlaying={() => setLoading(false)}
          onWaiting={() => setLoading(true)}
          onPause={() => {
            setIsPlaying(false);
            setLoading(false);
          }}
          onError={() => {
            setIsPlaying(false);
            setLoading(false);
          }}
          className="hidden"
        />
      ) : null}

    </div>
  );
}
