import type { Metadata } from "next";
import { PlatformOverview } from "@/domains/platform";

export const metadata: Metadata = { title: "Platform" };

export default function PlatformPage() {
  return <PlatformOverview />;
}
