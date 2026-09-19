import { CircuitConsole } from "@/domains/assess";

export default async function CircuitPage({
  params,
}: {
  params: Promise<{ orgSlug: string; circuitId: string }>;
}) {
  const { orgSlug, circuitId } = await params;
  return <CircuitConsole orgSlug={orgSlug} circuitId={circuitId} />;
}
