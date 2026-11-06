"use client";

import { useState } from "react";
import { AsyncBoundary, b2bTokens as t, cn } from "@/foundation/ui";
import { acts, card, fields } from "@/domains/assess/ui";
import { useAsync } from "@/foundation/hooks";
import { formatWhen } from "@/domains/assess/team/chrome";
import { listAudit, type AuditFilters } from "@/domains/assess/team/api";
import { boardBtn, boardPadWide, boardInput, boardLabel } from "@/foundation/ui/boardKit";

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
  const [draft, setDraft] = useState<AuditFilters>({
    actorEmail: "",
    action: "",
  });
  const [filters, setFilters] = useState<AuditFilters>({});
  const filtering = Boolean(filters.actorEmail || filters.action);

  const state = useAsync(
    (signal) => listAudit(orgSlug, signal, undefined, filters),
    [orgSlug, filters.actorEmail, filters.action],
  );

  return (
    <div className="flex flex-col gap-6">
      <form
        className={boardPadWide}
        onSubmit={(event) => {
          event.preventDefault();
          setFilters({
            actorEmail: draft.actorEmail?.trim() || null,
            action: draft.action?.trim() || null,
          });
        }}
      >
        <div className={fields}>
          <div>
            <label htmlFor="audit-actor" className={boardLabel}>
              Done by
            </label>
            <input
              id="audit-actor"
              className={boardInput}
              type="email"
              placeholder="name@hospital.nhs.uk"
              value={draft.actorEmail ?? ""}
              onChange={(event) =>
                setDraft((prev) => ({
                  ...prev,
                  actorEmail: event.target.value,
                }))
              }
            />
          </div>
          <div>
            <label htmlFor="audit-action" className={boardLabel}>
              Action
            </label>
            <input
              id="audit-action"
              className={boardInput}
              placeholder="e.g. membership."
              value={draft.action ?? ""}
              onChange={(event) =>
                setDraft((prev) => ({ ...prev, action: event.target.value }))
              }
            />
          </div>
        </div>
        <div className={acts}>
          <button type="submit" className={boardBtn()}>
            Filter
          </button>
          <button
            type="button"
            className={boardBtn("ghost")}
            onClick={() => {
              setDraft({ actorEmail: "", action: "" });
              setFilters({});
            }}
          >
            Clear
          </button>
        </div>
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
          <div className={card}>
            {page.items.map((event, index) => (
              <div
                key={event.id}
                className={cn(
                  "flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-5 py-4",
                  index > 0 && "border-t border-osce-border-light",
                )}
              >
                <div className="min-w-0 flex-[1_1_260px]">
                  <div className="text-assess-label font-semibold text-osce-ink-900">
                    {event.summary ?? event.action}
                  </div>
                  {event.actor_email ? (
                    <div className={t.assessMeta}>By {event.actor_email}</div>
                  ) : null}
                </div>
                <time
                  className={cn(t.assessMeta, "shrink-0")}
                  dateTime={event.at}
                >
                  {formatWhen(event.at)}
                </time>
              </div>
            ))}
          </div>
        )}
      </AsyncBoundary>
    </div>
  );
}
