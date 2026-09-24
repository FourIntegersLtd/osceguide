import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { CreateStationScreen } from "@/capabilities/authoring/stations/CreateStationScreen";

export const metadata: Metadata = { title: "New station" };

export default function Page() {
  return (
    <Capability id="authoring">
      <CreateStationScreen />
    </Capability>
  );
}
