import type { Metadata } from "next";
import { CreateStationScreen } from "@/capabilities/authoring/stations/CreateStationScreen";

export const metadata: Metadata = { title: "New station" };

export default function Page() {
  return <CreateStationScreen />;
}
