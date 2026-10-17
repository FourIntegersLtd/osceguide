"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Alert, Spinner } from "@/foundation/ui";
import { errorMessage, useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { readAttemptBrief } from "@/capabilities/attempt-runner";
import { listSets } from "@/domains/train/api";
import { attemptDestination } from "@/domains/train/station/attemptDestination";

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
      return { brief, setId: brief.set_entry_id ? await setHolding(brief.set_entry_id, signal) : null };
    },
    [attemptId],
  );

  const destination = state.data ? attemptDestination(state.data.brief, state.data.setId) : null;
  const review = `?action=review&tab=feedback&attempt=${attemptId}`;
  const href =
    destination?.kind === "set_entry"
      ? `${hrefFor(`/mocks/${destination.setId}/stations/${destination.entryId}`)}${review}`
      : destination?.kind === "station"
        ? `${hrefFor(`/stations/${destination.stationId}/practise`)}${review}`
        : null;

  useEffect(() => {
    // `replace`, so Back goes where they came from rather than through here.
    if (href) router.replace(href);
  }, [href, router]);

  if (state.error) {
    return <Alert tone="danger">{errorMessage(state.error)}</Alert>;
  }

  if (destination?.kind === "unknown") {
    return (
      <Alert tone="warning" title="We could not find where this attempt was sat">
        <p>Its practice session or station may have been removed. Your other attempts are in your history.</p>
      </Alert>
    );
  }

  return (
    <div className="flex justify-center py-16">
      <Spinner size="md" className="text-ink-subtle" />
    </div>
  );
}

/** How many pages of sessions are read before giving up on finding one. */
const MAX_SET_PAGES = 20;

/** The session holding this entry, walking the person's sessions a page at a time. */
async function setHolding(entryId: string, signal: AbortSignal): Promise<string | null> {
  let cursor: string | null = null;
  for (let pages = 0; pages < MAX_SET_PAGES; pages += 1) {
    const page = await listSets(signal, cursor);
    const set = page.items.find((candidate) => (candidate.entries ?? []).some((entry) => entry.id === entryId));
    if (set) return set.id;
    cursor = page.next_cursor ?? null;
    if (!cursor) return null;
  }
  // Not finding it in the pages read does not mean it was removed.
  throw new Error("We could not find the session this attempt belongs to. Please try again.");
}
