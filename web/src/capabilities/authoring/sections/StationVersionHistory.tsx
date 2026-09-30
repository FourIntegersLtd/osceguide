"use client";

import { useState } from "react";
import { AsyncBoundary } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { listStationVersions, type StationVersion } from "@/capabilities/stations";
import { AuthoringCard } from "@/capabilities/authoring/parts/AuthoringCard";
import { StatusBadge } from "@/capabilities/authoring/parts/StatusPills";
import { usedByLabel } from "@/capabilities/authoring/sections/StationUsedBy";

/**
 * Every revision this station has had, newest first.
 *
 * The lifecycle could draft, publish, supersede and archive a version and had
 * no reader for any of it, so an author looking at a station could not see the
 * ones behind it. `GET /api/v1/stations/{id}/versions` is that reader, and it
 * is staff-only because each row is the whole document — including the drafts
 * nobody settled on — so this disclosure is the author's own view of their
 * material, not a candidate's.
 *
 * It is a disclosure rather than a page because it answers a question asked
 * once in a while from inside the station that is already on screen, and a
 * fourth arm mounting this capability should not have to route for it. The
 * history is read the first time it is opened: nobody who is not curious should
 * pay a request for it.
 */
export function StationVersionHistory({ stationId }: { stationId: string }) {
  const [asked, setAsked] = useState(false);
  const versions = useAsync(
    (signal) => (asked ? listStationVersions(stationId, signal) : Promise.resolve<StationVersion[]>([])),
    [stationId, asked],
  );

  return (
    <AuthoringCard padding="md">
      <details
        onToggle={(event) => {
          if (!asked && event.currentTarget.open) setAsked(true);
        }}
      >
        <summary className="cursor-pointer text-osce-body font-medium text-b2b-headline">
          Revision history
        </summary>

        {asked ? (
          <div className="mt-3">
            <AsyncBoundary
              state={versions}
              isEmpty={(rows) => rows.length === 0}
              empty={{
                title: "No revisions listed",
                description: "This station has one version, and it is the one above.",
              }}
            >
              {(rows) => (
                <ul className="divide-y divide-b2b-border border-y border-b2b-border">
                  {rows.map((item) => (
                    <li key={item.id} className="flex items-center gap-3 py-2">
                      <span className="w-14 shrink-0 text-osce-body text-b2b-headline">
                        v{item.version}
                      </span>
                      <StatusBadge status={item.status} />
                      <span className="min-w-0 flex-1 text-osce-caption text-b2b-mid">
                        {stamp(item)}
                        {typeof item.used_by_count === "number"
                          ? ` · ${usedByLabel(item.used_by_count)}`
                          : ""}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </AsyncBoundary>
          </div>
        ) : null}
      </details>
    </AuthoringCard>
  );
}

/** What a revision was last doing: published, then archived, or still a draft. */
function stamp(version: StationVersion): string {
  if (version.archived_at) return `Archived ${new Date(version.archived_at).toLocaleDateString()}`;
  if (version.published_at) return `Published ${new Date(version.published_at).toLocaleDateString()}`;
  return "Never published";
}
