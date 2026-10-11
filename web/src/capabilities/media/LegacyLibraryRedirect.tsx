"use client";

import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities/SurfaceContext";
import { readMedia } from "@/capabilities/media/api";
import { mediaKindOf } from "@/capabilities/media/MediaCard";
import { StudyTabRedirect } from "@/capabilities/media/StudyTabRedirect";
import { studyItemHref } from "@/capabilities/media/studyPaths";

/** An old `/library/<slug>` link: read the item, then send it to its kind's own page. */
export function LegacyLibraryRedirect({ slug }: { slug: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => readMedia(slug, signal), [slug]);
  return (
    <div className="w-full text-left">
      <AsyncBoundary state={state}>
        {(item) => <StudyTabRedirect hrefFor={(path) => path} path={studyItemHref(hrefFor, mediaKindOf(item) ?? "blog", item.slug)} />}
      </AsyncBoundary>
    </div>
  );
}
