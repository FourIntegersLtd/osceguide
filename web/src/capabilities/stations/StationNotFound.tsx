"use client";

import { B2CEmptyState } from "@/foundation/ui";

/**
 * A station id that names nothing this person may read.
 *
 * `GET /api/v1/stations/{id}` answers `station_not_found` for a withdrawn case,
 * for one that was never published, and for another tenant's private station
 * alike — which of them it was is somebody else's business. So the screens that
 * open a station by link all say the same sentence, and say it here.
 *
 * It is rendered by the caller rather than by `AsyncBoundary`'s `empty` prop,
 * because that prop never fires on a read that settled on `null`: the boundary
 * returns nothing for a null result, which is how a dead link came to look
 * like a blank page.
 */
export function StationNotFound() {
  return (
    <B2CEmptyState
      className="mt-8"
      title="We could not find that station"
      description="It may have been withdrawn, or replaced by a newer version."
    />
  );
}
