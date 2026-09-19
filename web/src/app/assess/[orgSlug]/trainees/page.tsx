import type { Metadata } from "next";
import { RequireCapability } from "@/foundation/session";
import { Trainees } from "@/domains/assess";

export const metadata: Metadata = { title: "Trainees" };

export default async function TraineesPage({ params }: { params: Promise<{ orgSlug: string }> }) {
  const { orgSlug } = await params;
  return (
    <RequireCapability permission="read_org">
      <Trainees orgSlug={orgSlug} />
    </RequireCapability>
  );
}
