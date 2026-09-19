import type { Metadata } from "next";
import { Screen } from "@/app/app/[workspace]/screen";
export const metadata: Metadata = { title: "Your attempt" };


export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; attemptId: string }>;
}) {
  const { workspace, attemptId } = await params;
  return <Screen name="attempt" slug={workspace} params={{ attemptId }} />;
}
