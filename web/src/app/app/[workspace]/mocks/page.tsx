import type { Metadata } from "next";
import { Screen } from "@/app/app/[workspace]/screen";
export const metadata: Metadata = { title: "Practice sessions" };


export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string }>;
}) {
  const { workspace } = await params;
  return <Screen name="mocks" slug={workspace} />;
}
