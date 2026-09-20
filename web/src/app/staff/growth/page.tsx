import type { Metadata } from "next";
import { GrowthDashboard } from "@/capabilities/staff-growth/GrowthDashboard";

export const metadata: Metadata = { title: "Growth" };

export default function Page() {
  return <GrowthDashboard />;
}
