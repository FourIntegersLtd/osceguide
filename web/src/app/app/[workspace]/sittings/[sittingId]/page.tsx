import { Screen } from "@/app/app/[workspace]/screen";

export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; sittingId: string }>;
}) {
  const { workspace, sittingId } = await params;
  return <Screen name="sittingDetail" slug={workspace} params={{ sittingId }} />;
}
