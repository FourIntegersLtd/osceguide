"use client";

import { AsyncBoundary, Badge, Button, Spinner } from "@/foundation/ui";
import { StationFilters } from "@/capabilities/stations/StationFilters";
import { StationIdentity } from "@/capabilities/stations/LibraryBrowse";
import type { StationLibraryScope } from "@/capabilities/stations/api";
import { useStationLibrary } from "@/capabilities/stations/useStationLibrary";
import type { LibraryStation } from "@/capabilities/stations/api";

export interface StationPickerProps {
  onPick: (station: LibraryStation) => void;
  pickLabel?: string;
  selectedVersionIds?: ReadonlySet<string>;
  /** Whose stations are offered, and for which exam. Left out, the signed-in user's own exam's library. */
  scope?: StationLibraryScope;
}

/**
 * The library as a picker, embedded in somebody else's form.
 *
 * `onPick` is how a surface uses the library for its own purpose without the
 * library learning about it: Train passes "add to my mock", Assess passes "put
 * this on the circuit", and the component itself has no opinion. It carries no
 * page header, because it is never the page — it sits inside the card that
 * builds a mock or a circuit.
 */
export function StationPicker({
  onPick,
  pickLabel = "Select",
  selectedVersionIds,
  scope,
}: StationPickerProps) {
  const library = useStationLibrary(scope);
  const state = {
    ...library.first,
    data: library.first.data === null ? null : library.stations,
  };

  return (
    <div className="flex flex-col gap-4">
      <StationFilters library={library} />

      <AsyncBoundary
        state={state}
        isEmpty={(rows) => rows.length === 0}
        empty={{
          title: "No stations here yet",
          description: library.examCode
            ? `Published stations for ${library.examCode.toUpperCase()} will appear here.`
            : "Published stations for this exam will appear here.",
        }}
      >
        {(rows) => (
          <>
            <ul className="divide-y divide-border rounded-panel border border-border bg-surface">
              {rows.map((station) => {
                const added = selectedVersionIds?.has(station.version_id) ?? false;
                return (
                  <li
                    key={station.version_id}
                    className="flex flex-wrap items-center justify-between gap-3 px-4 py-3"
                  >
                    <StationIdentity station={station} />
                    <div className="flex items-center gap-3">
                      <Badge tone="accent">{station.exam_code.toUpperCase()}</Badge>
                      <button
                        type="button"
                        onClick={() => onPick(station)}
                        disabled={added}
                        className="rounded-control border border-border-strong px-3 py-1 text-sm font-medium text-ink hover:bg-surface-raised disabled:cursor-not-allowed disabled:text-ink-subtle"
                      >
                        {added ? "Added" : pickLabel}
                      </button>
                    </div>
                  </li>
                );
              })}
            </ul>

            {library.hasMore && (
              <div className="flex justify-center">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={library.loadMore}
                  disabled={library.loadingMore}
                >
                  {library.loadingMore ? <Spinner /> : "Load more stations"}
                </Button>
              </div>
            )}
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
