import type { Metadata } from "next";
import { RequireCapability } from "@/foundation/session";
import { Results } from "@/domains/assess";

export const metadata: Metadata = { title: "Results" };

export default async function ResultsPage({
  params,
}: {
  params: Promise<{ orgSlug: string; sittingId: string }>;
}) {
  const { orgSlug, sittingId } = await params;
  return (
    <RequireCapability permission="sign_off_results">
      <Results orgSlug={orgSlug} sittingId={sittingId} />
    </RequireCapability>
  );
}
