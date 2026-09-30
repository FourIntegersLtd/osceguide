import { Screen } from "@/app/app/[workspace]/screen";

export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; circuitId: string }>;
}) {
  const { workspace, circuitId } = await params;
  return <Screen name="circuitConsole" slug={workspace} params={{ circuitId }} />;
}
