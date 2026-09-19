import type { Metadata } from "next";
import { MyResult } from "@/domains/assess";

export const metadata: Metadata = { title: "Your result" };

export default async function MyResultPage({
  params,
}: {
  params: Promise<{ sittingId: string }>;
}) {
  const { sittingId } = await params;
  return <MyResult sittingId={sittingId} />;
}
