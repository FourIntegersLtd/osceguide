"use client";

import { useEffect, useRef } from "react";

/**
 * A product demo clip: muted, looping, with controls. Playback starts only when the visitor has
 * not asked for reduced motion (set via `play()` rather than `autoPlay` so server and client
 * markup stay identical) and only once the player scrolls into view, so a visitor who never
 * reaches it does not stream the whole file. The landing page and the peer-practice screen both
 * show the marketplace clip through this one player; each supplies its own frame.
 */
export function DemoVideo({
  src,
  title,
  className,
  controls = true,
  poster,
  eager = false,
}: {
  /** One file, or several `<source>` formats in order of preference. */
  src: string | readonly { src: string; type: string }[];
  /** Accessible name for the player. */
  title: string;
  className?: string;
  /** Hide the player controls when something around the clip handles the click (a preview). */
  controls?: boolean;
  /** Shown until playback starts, and for good when the visitor asked for reduced motion or data saving. */
  poster?: string;
  /** Start at once (an above-the-fold clip) instead of when scrolled into view. */
  eager?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) {
      return;
    }
    const saveData = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection?.saveData === true;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || saveData) {
      return;
    }
    const start = () =>
      void video.play().catch(() => {
        /* Autoplay can be blocked; the controls remain available. */
      });
    if (eager) {
      start();
      return;
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry?.isIntersecting) {
        return;
      }
      observer.disconnect();
      start();
    });
    observer.observe(video);
    return () => observer.disconnect();
  }, [eager]);

  return (
    <video
      ref={videoRef}
      className={className}
      src={typeof src === "string" ? src : undefined}
      poster={poster}
      title={title}
      aria-label={title}
      loop
      muted
      playsInline
      controls={controls}
      preload="metadata"
    >
      {typeof src !== "string" && src.map((s) => <source key={s.src} src={s.src} type={s.type} />)}
      Your browser does not support the video tag.
    </video>
  );
}
