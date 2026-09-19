import type { Metadata } from "next";
import { PeerPractice } from "@/capabilities/peer-practice";

export const metadata: Metadata = { title: "Practise with someone" };

export default function PeersPage() {
  return <PeerPractice />;
}
