"use client";

import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { listStationVersions } from "@/capabilities/stations";

/** What one count means, said the same way wherever a version is shown. */
export function usedByLabel(count: number): string {
  if (count === 0) return "Not used anywhere yet";
  return `Used ${count} time${count === 1 ? "" : "s"}: by circuits, attempts, peer sessions and practice sets`;
}

/**
 * What already names this version, said before somebody archives or deletes it.
 *
 * `used_by_count` sums the circuits, attempts, peer practice sessions and
 * practice sets that name the version. It is information, not a gate: the
 * backend still decides deletion by status. Read from the revision history,
 * the one read that carries it.
 */
export function StationUsedBy({ stationId, version }: { stationId: string; version: number }) {
  const versions = useAsync((signal) => listStationVersions(stationId, signal), [stationId]);
  return (
    <AsyncBoundary
      state={versions}
      loading={<span className="block text-osce-caption text-ink-muted">Checking what uses it…</span>}
      failure={(_error, retry) => (
        <span className="block text-osce-caption text-ink-muted">
          Could not check what uses this version.{" "}
          <button type="button" className="underline" onClick={retry}>
            Try again
          </button>
        </span>
      )}
    >
      {(rows) => {
        const count = rows.find((row) => row.version === version)?.used_by_count;
        if (count === null || count === undefined) return null;
        return (
          <span
            className={
              count > 0
                ? "block font-medium text-ink"
                : "block text-osce-caption text-ink-muted"
            }
          >
            v{version}: {usedByLabel(count)}.
          </span>
        );
      }}
    </AsyncBoundary>
  );
}
