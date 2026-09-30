import type { Metadata } from "next";
import { Screen } from "@/app/app/[workspace]/screen";
export const metadata: Metadata = { title: "New circuit" };


export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; sittingId: string }>;
}) {
  const { workspace, sittingId } = await params;
  return <Screen name="newCircuit" slug={workspace} params={{ sittingId }} />;
}
