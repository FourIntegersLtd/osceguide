import type { Metadata } from "next";
import { Suspense } from "react";
import { CreateStationScreen } from "@/capabilities/authoring/stations/CreateStationScreen";

export const metadata: Metadata = { title: "New station" };

export default function Page() {
  return (
    <Suspense fallback={null}>
      <CreateStationScreen />
    </Suspense>
  );
}
