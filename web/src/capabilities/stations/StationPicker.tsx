"use client";

import { LuCheck, LuStethoscope } from "react-icons/lu";
import { AsyncBoundary, Button, Spinner } from "@/foundation/ui";
import { StationFilters } from "@/capabilities/stations/StationFilters";
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
    <div className="flex min-h-0 flex-col gap-3">
      <StationFilters library={library} maxWidthClass="max-w-none" />

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
            <ul className="m-0 max-h-[min(22rem,50dvh)] list-none divide-y divide-border overflow-y-auto rounded-panel border border-border bg-surface p-0">
              {rows.map((station) => {
                const added = selectedVersionIds?.has(station.version_id) ?? false;
                return (
                  <li key={station.version_id} className="flex items-center gap-3 px-4 py-2.5">
                    <LuStethoscope className="h-4 w-4 shrink-0 text-ink-subtle" aria-hidden />
                    <div className="min-w-0 flex-1">
                      <p className="m-0 truncate text-sm font-medium text-ink" title={station.title}>
                        {station.title}
                      </p>
                      {station.version > 1 ? <p className="m-0 text-xs text-ink-subtle">Version {station.version}</p> : null}
                    </div>
                    <button
                      type="button"
                      onClick={() => onPick(station)}
                      disabled={added}
                      className="inline-flex min-h-9 w-24 shrink-0 items-center justify-center gap-1.5 rounded-control border border-border-strong px-3 text-sm font-medium text-ink hover:bg-surface-raised disabled:cursor-not-allowed disabled:text-ink-subtle"
                    >
                      {added ? <LuCheck className="h-4 w-4" aria-hidden /> : null}
                      {added ? "Added" : pickLabel}
                    </button>
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
                  {library.loadingMore ? <Spinner className="text-current" /> : "Load more stations"}
                </Button>
              </div>
            )}
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
