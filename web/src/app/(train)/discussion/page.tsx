import type { Metadata } from "next";
import { Discussion } from "@/capabilities/community";

export const metadata: Metadata = { title: "Discussion" };

export default function DiscussionPage() {
  return <Discussion />;
}
