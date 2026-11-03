"use client";

import { useState } from "react";
import { HiOutlineArrowsPointingOut } from "react-icons/hi2";
import { DemoVideo } from "@/foundation/ui/DemoVideo";
import Modal from "@/foundation/ui/Modal";
import {
  MARKETPLACE_VIDEO_SRC,
  MARKETPLACE_VIDEO_TITLE,
} from "@/capabilities/peer-practice/marketplace/copy";

/**
 * The marketplace "how it works" clip: a small muted preview that plays on its own, and a click
 * opens it large with sound and controls so the steps can be followed.
 */
export function MarketplaceVideo({ className }: { className?: string }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <>
      <button
        type="button"
        onClick={() => setExpanded(true)}
        aria-label={`${MARKETPLACE_VIDEO_TITLE}: expand the video`}
        className={`group relative block cursor-pointer overflow-hidden rounded-osce-lg ${className ?? ""}`}
      >
        <DemoVideo
          src={MARKETPLACE_VIDEO_SRC}
          title={MARKETPLACE_VIDEO_TITLE}
          controls={false}
          className="pointer-events-none aspect-video w-full object-contain"
        />
        <span className="absolute bottom-2 right-2 flex h-8 w-8 items-center justify-center rounded-full bg-black/55 text-white transition-colors group-hover:bg-black/75">
          <HiOutlineArrowsPointingOut className="h-4 w-4" aria-hidden />
        </span>
      </button>
      {expanded ? (
        <Modal
          title={MARKETPLACE_VIDEO_TITLE}
          width="min(96vw, 1100px)"
          height="fit-content"
          onClose={() => setExpanded(false)}
        >
          {/* Plain player with sound: the viewer asked to watch it, so it is not muted. The clip
              has no caption track to point at yet. */}
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <video
            className="aspect-video w-full rounded-osce-lg bg-black"
            src={MARKETPLACE_VIDEO_SRC}
            title={MARKETPLACE_VIDEO_TITLE}
            aria-label={MARKETPLACE_VIDEO_TITLE}
            controls
            autoPlay
            playsInline
          />
        </Modal>
      ) : null}
    </>
  );
}
