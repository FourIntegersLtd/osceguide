"use client";

import { DemoVideo } from "@/foundation/ui/DemoVideo";

type LandingDemoVideoProps = {
  src: string;
  /** Accessible name for the player. */
  title: string;
  className?: string;
};

/** Product demo clip in the same white showcase frame as the hero report. */
export function LandingDemoVideo({
  src,
  title,
  className = "",
}: LandingDemoVideoProps) {
  return (
    <div
      className={`overflow-hidden rounded-2xl border border-site-line bg-site-card p-1.5 shadow-sm sm:p-2 ${className}`}
    >
      <DemoVideo
        src={src}
        title={title}
        className="aspect-video h-full w-full rounded-xl bg-site-pale object-contain"
      />
    </div>
  );
}
