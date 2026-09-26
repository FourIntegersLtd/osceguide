/* The live practice session with another candidate: preparation, the video call and the debrief. */

import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { PeerSessionScreen } from "@/capabilities/peer-practice";

export const metadata: Metadata = { title: "Practice session" };

export default async function Page({ params }: { params: Promise<{ workspace: string; sessionId: string }> }) {
  const { sessionId } = await params;
  return <Capability id="peer-practice"><PeerSessionScreen sessionId={sessionId} /></Capability>;
}
