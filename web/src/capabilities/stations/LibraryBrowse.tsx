"use client";

import Link from "next/link";
import { LuChevronRight, LuStethoscope } from "react-icons/lu";
import { Alert, AsyncBoundary, Badge, Button, B2CPageHeader, Spinner } from "@/foundation/ui";
import { useSurface } from "@/capabilities/SurfaceContext";
import { libraryFailure } from "@/capabilities/stations/libraryPaging";
import { StationFilters } from "@/capabilities/stations/StationFilters";
import { stationHref } from "@/capabilities/stations/routes";
import { useStationLibrary } from "@/capabilities/stations/useStationLibrary";
import type { LibraryStation } from "@/capabilities/stations/api";

/**
 * The library, browsable.
 *
 * Mounted unchanged on a person's own workspace, on an institution's and on an
 * employer's: the rows are the same rows, and the only thing that differs is
 * the base path the links hang off, which comes from the surface context. The
 * retiring client had this list four times — once per consumer product — and
 * institutions had no way to see it at all.
 */
export function LibraryBrowse() {
  const { hrefFor, orgSlug, surface } = useSurface();
  // Inside an organisation this is its own library, not the signed-in user's consumer exam's.
  const library = useStationLibrary({ orgSlug });

  // The boundary reports on the first page; the filtered rows are what renders.
  const state = {
    ...library.first,
    data: library.first.data === null ? null : library.stations,
  };

  return (
    <div className="flex flex-col gap-5">
      <B2CPageHeader
        title="Station library"
        subtitle="Every scenario published for the exams you have access to."
      />

      <StationFilters library={library} />

      <AsyncBoundary
        state={state}
        failure={
          state.error && libraryFailure(state.error, surface).paywall
            ? (error) => (
                <Alert tone="warning" title="This exam's stations are not open to you">
                  <p>{libraryFailure(error, surface).text}</p>
                </Alert>
              )
            : undefined
        }
        isEmpty={(rows) => rows.length === 0}
        empty={
          library.applied
            ? {
                title: "Nothing matches that",
                description: `No published station has "${library.applied}" in its title. Try a shorter word, or clear the search.`,
                action: (
                  <Button variant="secondary" size="sm" onClick={() => library.clearSearch()}>
                    Clear search
                  </Button>
                ),
              }
            : {
                title: "No stations here yet",
                description: "Published stations for this exam will appear here.",
              }
        }
      >
        {(rows) => (
          <>
            <ul className="divide-y divide-border rounded-panel border border-border bg-surface">
              {rows.map((station) => (
                <li key={station.version_id}>
                  <Link
                    href={stationHref(hrefFor, station.id)}
                    className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 transition-colors hover:bg-surface-raised"
                  >
                    <StationIdentity station={station} />
                    <div className="flex items-center gap-3">
                      <Badge tone="accent">{station.exam_code.toUpperCase()}</Badge>
                      <LuChevronRight className="h-4 w-4 text-ink-subtle" aria-hidden />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>

            {library.moreError && (
              <Alert tone="danger" title="More stations did not load">
                <p>{libraryFailure(library.moreError, surface).text}</p>
              </Alert>
            )}
            {library.hasMore && (
              <div className="flex justify-center">
                <Button
                  variant="secondary"
                  onClick={library.loadMore}
                  disabled={library.loadingMore}
                >
                  {library.loadingMore ? <Spinner className="text-current" /> : library.moreError ? "Try again" : "Load more stations"}
                </Button>
              </div>
            )}
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}

/** The identifying half of a row: the icon, the title and the version. */
export function StationIdentity({ station }: { station: LibraryStation }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <LuStethoscope className="h-4 w-4 shrink-0 text-ink-subtle" aria-hidden />
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-ink">{station.title}</p>
        <p className="text-xs text-ink-subtle">Version {station.version}</p>
      </div>
    </div>
  );
}
