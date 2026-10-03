import type { Metadata } from "next";
import { Screen } from "@/app/app/[workspace]/screen";

export const metadata: Metadata = { title: "Programme" };

export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; programmeId: string }>;
}) {
  const { workspace, programmeId } = await params;
  return <Screen name="programmeDetail" slug={workspace} params={{ programmeId }} />;
}
