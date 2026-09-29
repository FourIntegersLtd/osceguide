"use client";

import { useState } from "react";
import { AsyncBoundary, Button, Input, b2bTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { formatWhen } from "@/domains/assess/team/chrome";
import { listAudit, type AuditFilters } from "@/domains/assess/team/api";
import { auditMatches } from "@/domains/assess/team/support";

/**
 * The history tab: who added, changed or removed people and groups.
 *
 * The old tab kept its own `useEffect`, its own cancellation flag and its own
 * three pieces of state; this is the same list through `useAsync`, so a
 * failure is a failure with a retry rather than an empty log.
 *
 * Filtering by who and by what is the server's. A server that has not learnt
 * the filters yet answers unfiltered rows; those are filtered here, and the
 * screen says it only looked at the latest page, because "nothing matches"
 * over one page is not "nothing matches".
 */
export function ActivityPanel({ orgSlug }: { orgSlug: string }) {
  const [draft, setDraft] = useState<AuditFilters>({ actorEmail: "", action: "" });
  const [filters, setFilters] = useState<AuditFilters>({});
  const filtering = Boolean(filters.actorEmail || filters.action);

  const state = useAsync(
    async (signal) => {
      const page = await listAudit(orgSlug, signal, undefined, filters);
      const serverFiltered = page.items.every((entry) => auditMatches(entry, filters));
      return {
        items: page.items.filter((entry) => auditMatches(entry, filters)),
        partial: !serverFiltered,
        scanned: page.items.length,
      };
    },
    [orgSlug, filters.actorEmail, filters.action],
  );

  return (
    <div className="flex flex-col gap-3">
      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          setFilters({
            actorEmail: draft.actorEmail?.trim() || null,
            action: draft.action?.trim() || null,
          });
        }}
      >
        <Input
          label="Done by"
          type="email"
          placeholder="name@hospital.nhs.uk"
          value={draft.actorEmail ?? ""}
          onChange={(event) => setDraft((prev) => ({ ...prev, actorEmail: event.target.value }))}
        />
        <Input
          label="Action"
          placeholder="e.g. membership."
          value={draft.action ?? ""}
          onChange={(event) => setDraft((prev) => ({ ...prev, action: event.target.value }))}
        />
        <Button themeType="b2b" variant="secondary" type="submit">
          Filter
        </Button>
        {filtering ? (
          <Button
            themeType="b2b"
            variant="ghost"
            type="button"
            onClick={() => {
              setDraft({ actorEmail: "", action: "" });
              setFilters({});
            }}
          >
            Clear
          </Button>
        ) : null}
      </form>

      <AsyncBoundary
        state={state}
        isEmpty={(result) => result.items.length === 0}
        empty={
          filtering
            ? {
                title: "Nothing matches those filters.",
                description: state.data?.partial
                  ? `Only the latest ${state.data.scanned} entries were searched.`
                  : "Try a different address or action.",
              }
            : {
                title: "Nothing here yet.",
                description:
                  "Invitations, role changes and roster edits appear here as they happen.",
              }
        }
      >
        {(result) => (
          <>
            {filtering && result.partial ? (
              <p className="text-osce-caption text-b2b-mid">
                Showing matches among the latest {result.scanned} entries.
              </p>
            ) : null}
            <div className={b2bTokens.b2bGroupedShell}>
              <ul className="divide-y divide-b2b-border">
                {result.items.map((event) => (
                  <li key={event.id} className="px-4 py-3">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <p className="text-osce-body font-medium text-b2b-headline">
                        {event.summary ?? event.action}
                      </p>
                      <time className="shrink-0 text-osce-caption text-b2b-mid" dateTime={event.at}>
                        {formatWhen(event.at)}
                      </time>
                    </div>
                    {event.actor_email ? (
                      <p className="mt-0.5 text-osce-caption text-b2b-icon">By {event.actor_email}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </AsyncBoundary>
    </div>
  );
}
