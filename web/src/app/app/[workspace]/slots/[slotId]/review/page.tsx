import type { Metadata } from "next";
import { Screen } from "@/app/app/[workspace]/screen";
export const metadata: Metadata = { title: "Review" };


export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ workspace: string; slotId: string }>;
  searchParams: Promise<{ attempt?: string }>;
}) {
  const { workspace, slotId } = await params;
  const { attempt } = await searchParams;
  return (
    <Screen name="slotReview" slug={workspace} params={{ slotId, attemptId: attempt ?? "" }} />
  );
}
