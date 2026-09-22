"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { HiArrowRight } from "react-icons/hi";
import { HiOutlineFaceFrown } from "react-icons/hi2";
import { AsyncBoundary, B2CEmptyState, ButtonLink, cn, productTokens } from "@/foundation/ui";
import { useAsync } from "@/foundation/hooks";
import { useSurface } from "@/capabilities";
import { listMyAttempts } from "@/capabilities/attempt-runner";

const { b2cTableCell, b2cTableHeader, b2cTableThead } = productTokens;

export function FeedbackHistory({ stationVersionId, entryId, stationName }: {
  stationVersionId: string | null;
  entryId: string | null;
  stationName: string;
}) {
  const { hrefFor } = useSurface();
  const pathname = usePathname();
  const state = useAsync(async (signal) => {
    if (!stationVersionId && !entryId) return [];
    const items = [];
    let cursor: string | null | undefined;
    do {
      const page = await listMyAttempts({ stationVersionId, setEntryId: entryId, limit: 100, cursor }, signal);
      items.push(...page.items.filter((item) => item.has_result && item.kind !== "debrief"));
      cursor = page.next_cursor;
    } while (cursor && !signal.aborted);
    return items;
  }, [stationVersionId, entryId]);

  return <AsyncBoundary state={state}>{(items) => items.length === 0 ? (
    <div className="rounded-lg bg-b2c-surface-muted p-10 text-center">
      <B2CEmptyState icon={HiOutlineFaceFrown} title="No Feedback History Found"
        description="You haven't received any feedback for this station yet." />
      <ButtonLink href={pathname + "?action=attempt"} className="mt-4">Attempt this station</ButtonLink>
    </div>
  ) : (
    <div className="space-y-6">
      <h1 className="text-left text-osce-body font-semibold text-osce-ink-900">Feedbacks for {stationName}</h1>
      <div className="overflow-x-auto rounded-lg border border-b2c-border">
        <table data-b2c-table="" className="min-w-full divide-y divide-b2c-border">
          <thead className={b2cTableThead}><tr>{["#", "Date", "Evaluator", "Action"].map((label) =>
            <th key={label} className={cn("px-6 py-3 text-left", b2cTableHeader)}>{label}</th>
          )}</tr></thead>
          <tbody className="divide-y divide-b2c-border bg-osce-surface">
            {items.map((item, index) => <tr key={item.id} className="transition-colors hover:bg-b2c-surface-muted">
              <td className={cn("whitespace-nowrap px-6 py-4", b2cTableCell)}>
                <span className="rounded-full bg-b2c-secondary px-3 py-1 text-osce-data text-osce-ink-900">{index + 1}</span>
              </td>
              <td className={cn("whitespace-nowrap px-6 py-4", b2cTableCell)}>{new Date(item.created_at).toLocaleDateString("en-GB", {day:"numeric",month:"long",year:"numeric"})}</td>
              <td className={cn("whitespace-nowrap px-6 py-4", b2cTableCell)}>system</td>
              <td className={cn("whitespace-nowrap px-6 py-4", b2cTableCell)}>
                <Link href={hrefFor(`/attempts/${item.id}`)} className="group flex items-center space-x-2 text-osce-accent">
                  <span className="font-medium">View Details</span><HiArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Link>
              </td>
            </tr>)}
          </tbody>
        </table>
      </div>
    </div>
  )}</AsyncBoundary>;
}
