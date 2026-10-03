import type { Metadata } from "next";
import { Screen } from "@/app/app/[workspace]/screen";

export const metadata: Metadata = { title: "Review request" };

export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; reviewId: string }>;
}) {
  const { workspace, reviewId } = await params;
  return <Screen name="sharedReview" slug={workspace} params={{ reviewId }} />;
}
