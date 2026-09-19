"use client";

import Link from "next/link";
import { AsyncBoundary, Badge, ButtonLink, Card, PageHeader } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listSittings } from "@/domains/assess/api";

/** Scheduled examinations and training sessions. */
export function Sittings({ orgSlug }: { orgSlug: string }) {
  const { hrefFor } = useSurface();
  const state = useAsync((signal) => listSittings(orgSlug, signal), [orgSlug]);

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Sittings"
        description="Examinations and training sessions your organisation runs."
        actions={<ButtonLink href={hrefFor("/sittings/new")}>Schedule a sitting</ButtonLink>}
      />

      <AsyncBoundary
        state={state}
        isEmpty={(page) => page.items.length === 0}
        empty={{
          title: "No sittings yet",
          description: "Schedule one against a programme to get started.",
        }}
      >
        {(page) => (
          <ul className="flex flex-col gap-2">
            {page.items.map((sitting) => (
              <li key={sitting.id}>
                <Link href={hrefFor(`/sittings/${sitting.id}`)}>
                  <Card className="transition-colors hover:border-border-strong">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium text-ink">{sitting.name}</p>
                        <p className="text-xs text-ink-subtle">
                          {sitting.scheduled_for
                            ? new Date(sitting.scheduled_for).toLocaleString()
                            : "Not scheduled"}
                          {" · "}
                          {(sitting.circuits ?? []).length} circuit
                          {(sitting.circuits ?? []).length === 1 ? "" : "s"}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge tone="neutral">{sitting.mode}</Badge>
                        <Badge tone={sitting.status === "live" ? "success" : "neutral"}>
                          {sitting.status}
                        </Badge>
                      </div>
                    </div>
                  </Card>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </AsyncBoundary>
    </div>
  );
}
