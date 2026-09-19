import { Screen } from "@/app/app/[workspace]/screen";

export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; setId: string; entryId: string }>;
}) {
  const { workspace, setId, entryId } = await params;
  return <Screen name="mockStation" slug={workspace} params={{ setId, entryId }} />;
}
