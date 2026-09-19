import type { Metadata } from "next";
import { RequireCapability } from "@/foundation/session";
import { NewCircuit } from "@/domains/assess";

export const metadata: Metadata = { title: "Add a circuit" };

export default async function NewCircuitPage({
  params,
}: {
  params: Promise<{ orgSlug: string; sittingId: string }>;
}) {
  const { orgSlug, sittingId } = await params;
  return (
    <RequireCapability permission="manage_team">
      <NewCircuit orgSlug={orgSlug} sittingId={sittingId} />
    </RequireCapability>
  );
}
