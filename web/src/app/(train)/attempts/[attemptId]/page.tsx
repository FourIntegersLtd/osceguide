import type { Metadata } from "next";
import { AttemptResult } from "@/domains/train";

export const metadata: Metadata = { title: "Feedback" };

export default async function AttemptPage({
  params,
}: {
  params: Promise<{ attemptId: string }>;
}) {
  const { attemptId } = await params;
  return <AttemptResult attemptId={attemptId} />;
}
