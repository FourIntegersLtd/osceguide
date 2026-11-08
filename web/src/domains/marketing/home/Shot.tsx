import Image from "next/image";
import type { ReactNode } from "react";
import type { LandingShot } from "@/domains/marketing/home/landingShots";

/** The flat frame every capture and clip sits in: 1px line, 12px radius, no shadow. */
const SHOT_FRAME = "overflow-hidden rounded-xl border border-site-line bg-site-card";

export function Frame({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`${SHOT_FRAME} ${className}`}>{children}</div>;
}

/** A capture of the app, optimised by next/image from the 2x file. */
export function Shot({ shot, sizes, priority = false }: { shot: LandingShot; sizes: string; priority?: boolean }) {
  return (
    <Frame>
      <Image src={shot.src} alt={shot.alt} width={shot.width} height={shot.height} sizes={sizes} priority={priority} className="h-auto w-full" />
    </Frame>
  );
}
