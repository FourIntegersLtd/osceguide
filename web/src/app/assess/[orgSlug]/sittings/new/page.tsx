import type { Metadata } from "next";
import { RequireCapability } from "@/foundation/session";
import { NewSitting } from "@/domains/assess";

export const metadata: Metadata = { title: "Schedule a sitting" };

export default async function NewSittingPage({
  params,
}: {
  params: Promise<{ orgSlug: string }>;
}) {
  const { orgSlug } = await params;
  return (
    <RequireCapability permission="manage_team">
      <NewSitting orgSlug={orgSlug} />
    </RequireCapability>
  );
}
