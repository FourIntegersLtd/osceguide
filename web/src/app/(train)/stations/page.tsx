import type { Metadata } from "next";
import { StationLibrary } from "@/capabilities/stations";

export const metadata: Metadata = { title: "Stations" };

export default function StationsPage() {
  return <StationLibrary />;
}
