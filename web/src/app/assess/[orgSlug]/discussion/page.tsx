import type { Metadata } from "next";
import { OrgDiscussion } from "@/domains/assess/OrgDiscussion";

export const metadata: Metadata = { title: "Discussion" };

export default function OrgDiscussionPage() {
  return <OrgDiscussion />;
}
