import { MockStationRunner } from "@/domains/train";

export default async function StationRunnerPage({
  params,
}: {
  params: Promise<{ setId: string; entryId: string }>;
}) {
  const { setId, entryId } = await params;
  return <MockStationRunner setId={setId} entryId={entryId} />;
}
