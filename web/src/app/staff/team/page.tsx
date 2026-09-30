import type { Metadata } from "next";
import { PlatformTeam } from "@/domains/platform";

export const metadata: Metadata = { title: "Platform team" };

export default function Page() {
  return <PlatformTeam />;
}
