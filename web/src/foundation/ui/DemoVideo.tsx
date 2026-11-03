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
}: {
  src: string;
  /** Accessible name for the player. */
  title: string;
  className?: string;
  /** Hide the player controls when something around the clip handles the click (a preview). */
  controls?: boolean;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) {
      return;
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      return;
    }
    const observer = new IntersectionObserver(([entry]) => {
      if (!entry?.isIntersecting) {
        return;
      }
      observer.disconnect();
      void video.play().catch(() => {
        /* Autoplay can be blocked; the controls remain available. */
      });
    });
    observer.observe(video);
    return () => observer.disconnect();
  }, []);

  return (
    <video
      ref={videoRef}
      className={className}
      src={src}
      title={title}
      aria-label={title}
      loop
      muted
      playsInline
      controls={controls}
      preload="metadata"
    >
      Your browser does not support the video tag.
    </video>
  );
}
