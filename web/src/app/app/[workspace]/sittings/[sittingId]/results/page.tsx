import type { Metadata } from "next";
import { Screen } from "@/app/app/[workspace]/screen";
export const metadata: Metadata = { title: "Results" };


export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; sittingId: string }>;
}) {
  const { workspace, sittingId } = await params;
  return <Screen name="sittingResults" slug={workspace} params={{ sittingId }} />;
}
