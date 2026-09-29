"use client";

import { useState } from "react";
import { AsyncBoundary, Button, Input, b2bTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { formatWhen } from "@/domains/assess/team/chrome";
import { listAudit, type AuditFilters } from "@/domains/assess/team/api";

/**
 * The history tab: who added, changed or removed people and groups.
 *
 * The old tab kept its own `useEffect`, its own cancellation flag and its own
 * three pieces of state; this is the same list through `useAsync`, so a
 * failure is a failure with a retry rather than an empty log.
 *
 * Filtering by who (the address, exactly) and by what (an action or its
 * prefix, such as `membership.`) is the server's, as on the platform audit.
 */
export function ActivityPanel({ orgSlug }: { orgSlug: string }) {
  const [draft, setDraft] = useState<AuditFilters>({ actorEmail: "", action: "" });
  const [filters, setFilters] = useState<AuditFilters>({});
  const filtering = Boolean(filters.actorEmail || filters.action);

  const state = useAsync(
    (signal) => listAudit(orgSlug, signal, undefined, filters),
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
        isEmpty={(page) => page.items.length === 0}
        empty={
          filtering
            ? {
                title: "Nothing matches those filters.",
                description: "Try a different address or action.",
              }
            : {
                title: "Nothing here yet.",
                description:
                  "Invitations, role changes and roster edits appear here as they happen.",
              }
        }
      >
        {(page) => (
          <>
            <div className={b2bTokens.b2bGroupedShell}>
              <ul className="divide-y divide-b2b-border">
                {page.items.map((event) => (
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
