"use client";

import { useRef, useState } from "react";
import { HiOutlineChevronLeft, HiOutlineChevronRight, HiOutlinePhoto, HiOutlinePlay } from "react-icons/hi2";
import { B2CEmptyState, Button, cn, productTokens as t } from "@/foundation/ui";
import { deckSlides, deckVideoUrl, type MediaItem } from "@/capabilities/media/api";
import { Prose } from "@/capabilities/media/Prose";

/**
 * Chrome keeps the native control bar — and its dark scrim — painted over the
 * bottom of a paused video, which reads as a shadow on the first frame. Holding
 * `controls` back until the first play keeps the poster frame clean; from then on
 * the native controls behave normally, including while paused mid-video.
 */
function SlideVideoPlayer({ src }: { src: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [hasStarted, setHasStarted] = useState(false);

  return (
    <div className="relative w-full">
      {/* Slide videos have no caption track yet; the accessibility statement
          lists this as a known gap. */}
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <video
        ref={videoRef}
        src={src}
        controls={hasStarted}
        controlsList="nodownload noplaybackrate"
        onContextMenu={(event) => event.preventDefault()}
        onPlay={() => setHasStarted(true)}
        className="max-h-[min(70vh,720px)] w-full object-contain"
        playsInline
      />
      {!hasStarted && (
        <button
          type="button"
          onClick={() => videoRef.current?.play()}
          aria-label="Play video"
          className="absolute inset-0 flex items-center justify-center"
        >
          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-black/55 text-white transition hover:bg-black/70">
            <HiOutlinePlay className="ml-0.5 h-8 w-8" aria-hidden />
          </span>
        </button>
      )}
    </div>
  );
}

/**
 * The deck itself: a recorded presentation, or the slides one at a time.
 *
 * The retiring client only ever played a video, because that is what its
 * authoring tool produced. `platform-api` stores a `slides` array as well, so
 * both are read here and a deck published either way opens.
 */
export function DeckStage({ item }: { item: MediaItem }) {
  const video = deckVideoUrl(item);
  const slides = deckSlides(item);
  const [index, setIndex] = useState(0);

  if (video) return <SlideVideoPlayer key={video} src={video} />;

  if (slides.length === 0) {
    return (
      <B2CEmptyState
        icon={HiOutlinePhoto}
        title="No video available"
        description="This presentation does not have a video yet."
        className="border-0 bg-transparent shadow-none"
      />
    );
  }

  // Clamped rather than trusted: a deck edited between the list and the read
  // would otherwise index past the end and render a blank panel.
  const safeIndex = Math.min(index, slides.length - 1);
  const slide = slides[safeIndex];

  return (
    <div className="flex w-full flex-col gap-4">
      <div className={cn(t.b2cCard, "min-h-[220px] px-5 py-5")}>
        {slide?.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={slide.image_url} alt="" className="mb-4 w-full rounded-osce-md" />
        ) : null}
        {slide?.title ? (
          <h2 className={cn(t.b2cSectionTitle, "mb-2")}>{slide.title}</h2>
        ) : null}
        {slide?.body ? <Prose content={slide.body} /> : null}
      </div>

      <div className="flex items-center justify-between gap-4">
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setIndex(Math.max(0, safeIndex - 1))}
          disabled={safeIndex === 0}
        >
          <HiOutlineChevronLeft className="h-4 w-4" aria-hidden /> Previous
        </Button>
        <p aria-live="polite" className={t.b2cPanelCardMeta}>
          Slide {safeIndex + 1} of {slides.length}
        </p>
        <Button
          variant="secondary"
          size="sm"
          onClick={() => setIndex(Math.min(slides.length - 1, safeIndex + 1))}
          disabled={safeIndex === slides.length - 1}
        >
          Next <HiOutlineChevronRight className="h-4 w-4" aria-hidden />
        </Button>
      </div>
    </div>
  );
}
