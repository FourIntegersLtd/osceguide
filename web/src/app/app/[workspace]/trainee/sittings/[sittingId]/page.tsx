import type { Metadata } from "next";
import { Screen } from "@/app/app/[workspace]/screen";
export const metadata: Metadata = { title: "Your sitting" };


export default async function Page({
  params,
}: {
  params: Promise<{ workspace: string; sittingId: string }>;
}) {
  const { workspace, sittingId } = await params;
  return <Screen name="mySitting" slug={workspace} params={{ sittingId }} />;
}
