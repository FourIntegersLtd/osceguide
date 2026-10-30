"use client";

import { useEffect, useRef } from "react";

type LandingDemoVideoProps = {
  src: string;
  /** Accessible name for the player. */
  title: string;
  className?: string;
};

/**
 * Product demo clip in the same white showcase frame as the hero report.
 * Muted and looping, but playback only starts when the visitor has not asked
 * for reduced motion — set via `play()` rather than `autoPlay` so the server
 * and client markup stay identical — and only once the player scrolls into
 * view, so a visitor who never reaches it does not stream the whole file.
 */
export function LandingDemoVideo({
  src,
  title,
  className = "",
}: LandingDemoVideoProps) {
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
    <div
      className={`overflow-hidden rounded-2xl border border-site-line bg-site-card p-1.5 shadow-sm sm:p-2 ${className}`}
    >
      <video
        ref={videoRef}
        className="aspect-video h-full w-full rounded-xl bg-site-pale object-contain"
        src={src}
        title={title}
        aria-label={title}
        loop
        muted
        playsInline
        controls
        preload="metadata"
      >
        Your browser does not support the video tag.
      </video>
    </div>
  );
}
