import type { Metadata } from "next";
import { Screen } from "@/app/app/[workspace]/screen";
export const metadata: Metadata = { title: "My training" };


export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ workspace: string }>;
  searchParams: Promise<{ slot?: string }>;
}) {
  const { workspace } = await params;
  // A join link from the retiring client named a slot; the screen resolves it.
  const { slot } = await searchParams;
  return <Screen name="myTraining" slug={workspace} params={{ slot: slot ?? "" }} />;
}
