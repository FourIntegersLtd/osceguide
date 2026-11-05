import type { Metadata } from "next";
import { Suspense } from "react";
import { Capability } from "@/app/app/[workspace]/capability";
import { CreateStationScreen } from "@/capabilities/authoring/stations/CreateStationScreen";

export const metadata: Metadata = { title: "New station" };

export default function Page() {
  return (
    <Capability id="authoring">
      <Suspense fallback={null}>
        <CreateStationScreen />
      </Suspense>
    </Capability>
  );
}
