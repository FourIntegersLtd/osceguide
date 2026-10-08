import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { DebriefList } from "@/capabilities/debrief";

export const metadata: Metadata = { title: "Debriefs" };

export default function Page() {
  return <Capability id="debrief"><DebriefList /></Capability>;
}
