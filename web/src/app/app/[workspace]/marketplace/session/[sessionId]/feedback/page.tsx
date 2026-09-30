/* Where a practice session ends: the feedback on your partner, and the AI feedback notice for the doctor. */

import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { PeerSessionFeedbackPage } from "@/capabilities/peer-practice";

export const metadata: Metadata = { title: "Session feedback" };

export default async function Page({ params }: { params: Promise<{ workspace: string; sessionId: string }> }) {
  const { sessionId } = await params;
  return <Capability id="peer-practice"><PeerSessionFeedbackPage sessionId={sessionId} /></Capability>;
}
