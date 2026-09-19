"use client";

import { AsyncBoundary, b2bTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { formatWhen } from "@/domains/assess/team/chrome";
import { listAudit } from "@/domains/assess/team/api";

/**
 * The history tab: who added, changed or removed people and groups.
 *
 * The old tab kept its own `useEffect`, its own cancellation flag and its own
 * three pieces of state; this is the same list through `useAsync`, so a
 * failure is a failure with a retry rather than an empty log.
 */
export function ActivityPanel({ orgSlug }: { orgSlug: string }) {
  const state = useAsync((signal) => listAudit(orgSlug, signal), [orgSlug]);

  return (
    <AsyncBoundary
      state={state}
      isEmpty={(page) => page.items.length === 0}
      empty={{
        title: "Nothing here yet.",
        description: "Invitations, role changes and roster edits appear here as they happen.",
      }}
    >
      {(page) => (
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
      )}
    </AsyncBoundary>
  );
}
