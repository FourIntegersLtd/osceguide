import type { Metadata } from "next";
import { Suspense } from "react";
import { Capability } from "@/app/app/[workspace]/capability";
import { StationTemplateNewScreen } from "@/capabilities/authoring/templates/StationTemplateNewScreen";

export const metadata: Metadata = { title: "New station template" };

export default function Page() {
  return (
    <Capability id="authoring">
      <Suspense fallback={null}>
        <StationTemplateNewScreen />
      </Suspense>
    </Capability>
  );
}
