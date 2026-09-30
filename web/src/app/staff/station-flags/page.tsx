import type { Metadata } from "next";
import { StationFlags } from "@/domains/platform";

export const metadata: Metadata = { title: "Station reports" };

export default function Page() {
  return <StationFlags />;
}
