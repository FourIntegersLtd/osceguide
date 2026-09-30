import type { Metadata } from "next";
import { AttemptInspector } from "@/domains/platform";

export const metadata: Metadata = { title: "Attempt" };

/** One attempt, for support. Reached from an account's Attempts tab. */
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <AttemptInspector attemptId={id} />;
}
