import type { Metadata } from "next";
import { RequireCapability } from "@/foundation/session";
import { Team } from "@/domains/assess";

export const metadata: Metadata = { title: "Team" };

export default async function TeamPage({ params }: { params: Promise<{ orgSlug: string }> }) {
  const { orgSlug } = await params;
  return (
    <RequireCapability permission="manage_team">
      <Team orgSlug={orgSlug} />
    </RequireCapability>
  );
}
