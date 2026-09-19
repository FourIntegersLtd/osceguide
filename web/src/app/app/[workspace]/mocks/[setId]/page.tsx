import { Screen } from "@/app/app/[workspace]/screen";

export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; setId: string }>;
}) {
  const { workspace, setId } = await params;
  return <Screen name="mockDetail" slug={workspace} params={{ setId }} />;
}
