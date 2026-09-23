import type { Metadata } from "next";
import { Screen } from "@/app/app/[workspace]/screen";

export const metadata: Metadata = { title: "Edit circuit" };

export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; circuitId: string }>;
}) {
  const { workspace, circuitId } = await params;
  return <Screen name="circuitEdit" slug={workspace} params={{ circuitId }} />;
}
