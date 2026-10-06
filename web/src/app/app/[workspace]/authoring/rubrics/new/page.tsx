import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { RubricStartScreen } from "@/capabilities/authoring/rubrics/RubricStartScreen";

export const metadata: Metadata = { title: "New marking scheme" };

export default function Page() {
  return (
    <Capability id="authoring">
      <RubricStartScreen />
    </Capability>
  );
}
