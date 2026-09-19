"use client";

import Link from "next/link";
import { LuCircleCheck, LuPlay } from "react-icons/lu";
import { Alert, AsyncBoundary, Badge, ButtonLink, Card, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { browseLibrary } from "@/capabilities/stations";
import { readSet } from "@/domains/train/api";

/** A mock's stations, and where the candidate is up to in it. */
export function MockDetail({ setId }: { setId: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync(
    async (signal) => {
      const set = await readSet(setId, signal);
      // Entries carry a station version id and no title, so the library is the
      // lookup. One request for the exam beats one per entry.
      const library = await browseLibrary({ examCode: set.exam_code, limit: 200 }, signal);
      const titles = new Map(library.items.map((station) => [station.version_id, station.title]));
      return { set, titles };
    },
    [setId],
  );

  return (
    <div className="flex flex-col gap-6">
      <AsyncBoundary state={state}>
        {({ set, titles }) => (
          <>
            <PageHeader
              title={set.name}
              description={`${set.attempted_entries} of ${set.total_entries} stations attempted`}
              actions={<Badge tone="accent">{set.exam_code.toUpperCase()}</Badge>}
            />

            {set.locked && (
              <Alert tone="warning" title="This mock is locked">
                Your access to {set.exam_code.toUpperCase()} has lapsed. Renew it and this mock comes
                back exactly as you left it.
              </Alert>
            )}

            <ul className="flex flex-col gap-2">
              {(set.entries ?? [])
                .slice()
                .sort((a, b) => a.position - b.position)
                .map((entry) => (
                  <li key={entry.id}>
                    <Card>
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium text-ink">
                            {titles.get(entry.station_version_id) ?? "Station"}
                          </p>
                          <p className="text-xs text-ink-subtle">
                            {entry.attempts === 0
                              ? "Not attempted"
                              : `${entry.attempts} attempt${entry.attempts === 1 ? "" : "s"}`}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          {entry.attempts > 0 && (
                            <LuCircleCheck className="h-4 w-4 text-success" aria-hidden />
                          )}
                          {!set.locked && (
                            <ButtonLink
                              size="sm"
                              href={hrefFor(`/mocks/${set.id}/stations/${entry.id}`)}
                            >
                              <LuPlay className="h-3.5 w-3.5" aria-hidden />
                              {entry.attempts > 0 ? "Again" : "Start"}
                            </ButtonLink>
                          )}
                        </div>
                      </div>
                    </Card>
                  </li>
                ))}
            </ul>

            <Link href={hrefFor("/mocks")} className="text-sm text-ink-muted hover:text-ink">
              All mocks
            </Link>
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
