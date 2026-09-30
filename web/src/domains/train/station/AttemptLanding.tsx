"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Alert, LoadingSpinner } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readAttemptBrief } from "@/capabilities/attempt-runner";
import { listSets } from "@/domains/train/api";

/**
 * An attempt reached by its own id, sent on to where it is read.
 *
 * `/app/me/attempts/{id}` is the address in every link that points at one — a
 * feedback-ready notification, a bookmark, a row in a history table — and the
 * attempt itself is not a screen: what somebody wants is the station they sat,
 * open on its feedback.
 *
 * The brief says which station and, for a session's station, which entry; the
 * set it belongs to is the one holding that entry. That lookup is why this is
 * a screen rather than a redirect in middleware.
 */
export function AttemptLanding({ attemptId }: { attemptId: string }) {
  const router = useRouter();
  const { hrefFor } = useSurface();

  const state = useAsync(
    async (signal) => {
      const brief = await readAttemptBrief(attemptId, signal);
      if (!brief.set_entry_id) return { href: null, brief };

      const sets = await listSets(signal);
      const set = sets.items.find((candidate) =>
        (candidate.entries ?? []).some((entry) => entry.id === brief.set_entry_id),
      );
      return {
        brief,
        href: set
          ? `${hrefFor(`/mocks/${set.id}/stations/${brief.set_entry_id}`)}?action=review&tab=feedback&attempt=${attemptId}`
          : null,
      };
    },
    [attemptId],
  );

  const href =
    state.data?.href ??
    (state.data?.brief
      ? `${hrefFor(`/stations/${state.data.brief.station_id}/practise`)}?action=review&tab=feedback&attempt=${attemptId}`
      : null);

  useEffect(() => {
    // `replace`, so Back goes where they came from rather than through here.
    if (href) router.replace(href);
  }, [href, router]);

  if (state.error) {
    return <Alert tone="danger">{errorMessage(state.error)}</Alert>;
  }

  return (
    <div className="flex justify-center py-16">
      <LoadingSpinner />
    </div>
  );
}
