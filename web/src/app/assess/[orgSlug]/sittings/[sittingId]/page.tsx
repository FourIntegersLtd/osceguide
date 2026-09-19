import { SittingDetail } from "@/domains/assess";

export default async function SittingPage({
  params,
}: {
  params: Promise<{ orgSlug: string; sittingId: string }>;
}) {
  const { orgSlug, sittingId } = await params;
  return <SittingDetail orgSlug={orgSlug} sittingId={sittingId} />;
}
