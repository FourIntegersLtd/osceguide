import type { Metadata } from "next";
import { Screen } from "@/app/app/[workspace]/screen";
export const metadata: Metadata = { title: "Review" };


export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; slotId: string }>;
}) {
  const { workspace, slotId } = await params;
  return <Screen name="slotReview" slug={workspace} params={{ slotId }} />;
}
