"use client";

import { useRef, useState } from "react";
import { getImageProps } from "next/image";
import { DemoVideo } from "@/foundation/ui/DemoVideo";
import { Frame } from "@/domains/marketing/home/Shot";
import { HERO_CLIP_LABEL, HERO_CLIP_SOURCES, LANDING_SHOTS } from "@/domains/marketing/home/landingShots";

/** The hero clip: muted, looping, autoplaying. Reduced motion or data saving leaves the poster only. */
export function HeroClip() {
  const box = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(false);
  function toggle() {
    const v = box.current?.querySelector("video");
    if (!v) return;
    if (v.paused) void v.play();
    else v.pause();
    setPaused(v.paused);
  }
  const { props } = getImageProps({ src: LANDING_SHOTS.poster.src, width: LANDING_SHOTS.poster.width, height: LANDING_SHOTS.poster.height, alt: "", sizes: "(min-width: 1024px) 58vw, 100vw", priority: true });
  return (
    <div ref={box}>
    <Frame>
      <DemoVideo
        src={HERO_CLIP_SOURCES}
        title={HERO_CLIP_LABEL}
        poster={props.src}
        eager
        controls={false}
        className="block aspect-[13/10] w-full bg-site-card object-cover"
      />
    </Frame>
    <button type="button" onClick={toggle} className="mt-2 text-sm text-site-muted underline-offset-4 hover:text-site-brand hover:underline">
      {paused ? "Play the clip" : "Pause the clip"}
    </button>
    </div>
  );
}
