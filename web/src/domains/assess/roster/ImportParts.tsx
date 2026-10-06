"use client";

import { Alert } from "@/foundation/ui";
import type { BulkTraineesResult } from "@/domains/assess/roster/api";

/**
 * What a file should look like, and what happened to it.
 *
 * Both were inline in the old 150-line import step; they are here so the
 * dialog itself is the flow and nothing else.
 */
export function ImportInstructions() {
  return (
    <div className="space-y-3">
      <div className="rounded-panel border border-b2b-border bg-b2b-cream p-4">
        <p className="text-osce-body font-semibold text-b2b-headline">Required column</p>
        <p className="mt-1 text-osce-body text-b2b-graphite">
          <span className="font-mono">email</span>. Their email address
        </p>
      </div>
      <div className="rounded-panel border border-b2b-border bg-b2b-surface p-4">
        <p className="text-osce-body font-semibold text-b2b-headline">Optional columns</p>
        <ul className="mt-2 space-y-1.5 text-osce-body text-b2b-graphite">
          <li>
            <span className="font-mono">firstName</span>,{" "}
            <span className="font-mono">lastName</span>, or one <span className="font-mono">name</span> column. Their name
          </li>
          <li>
            <span className="font-mono">cohort</span> or <span className="font-mono">group</span>.
            The name of a cohort that already exists here (e.g. &quot;June 2026&quot;)
          </li>
        </ul>
      </div>
      <div className="rounded-panel border border-b2b-border bg-b2b-surface p-4">
        <p className="text-osce-body font-semibold text-b2b-headline">Example</p>
        <pre className="mt-2 overflow-auto rounded-control border border-b2b-border bg-b2b-cream p-3 text-osce-caption text-b2b-headline">
          email,firstName,lastName,cohort{"\n"}
          amina@hospital.nhs.uk,Amina,Khan,June 2026
        </pre>
      </div>
    </div>
  );
}

export function ImportOutcome({
  result,
  describe,
}: {
  result: BulkTraineesResult;
  describe: (code: string) => string;
}) {
  const created = result.created ?? [];
  const skipped = result.skipped ?? [];

  return (
    <div className="space-y-3">
      <Alert tone={created.length > 0 ? "success" : "warning"}>
        {created.length} added, {skipped.length} skipped.
      </Alert>
      {skipped.length > 0 ? (
        <div className="rounded-panel border border-b2b-border bg-b2b-surface p-4">
          <p className="text-osce-body font-semibold text-b2b-headline">Not imported</p>
          <ul className="mt-2 space-y-1 text-osce-body text-b2b-graphite">
            {skipped.map((row) => (
              <li key={row.email}>
                <span className="font-medium text-b2b-headline">{row.email}</span>:{" "}
                {describe(row.code)}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
