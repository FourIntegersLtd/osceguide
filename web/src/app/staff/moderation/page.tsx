import type { Metadata } from "next";
import { ModerationHome } from "@/capabilities/staff-moderation/ModerationHome";

export const metadata: Metadata = { title: "Moderation" };

export default function Page() {
  return <ModerationHome />;
}
