import type { Metadata } from "next";
import { RequireCapability } from "@/foundation/session";
import { SlotReview } from "@/domains/assess";

export const metadata: Metadata = { title: "Mark a station" };

/**
 * The attempt id arrives as a query parameter because the console already has
 * it: there is no single-slot read route, and adding a fetch to recover
 * something the caller knows would be a request per page view.
 */
export default async function SlotReviewPage({
  params,
  searchParams,
}: {
  params: Promise<{ orgSlug: string; slotId: string }>;
  searchParams: Promise<{ attempt?: string }>;
}) {
  const { orgSlug, slotId } = await params;
  const { attempt } = await searchParams;
  return (
    <RequireCapability permission="run_circuits">
      <SlotReview orgSlug={orgSlug} slotId={slotId} attemptId={attempt ?? null} />
    </RequireCapability>
  );
}
