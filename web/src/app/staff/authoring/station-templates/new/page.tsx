import type { Metadata } from "next";
import { Suspense } from "react";
import { StationTemplateNewScreen } from "@/capabilities/authoring/templates/StationTemplateNewScreen";

export const metadata: Metadata = { title: "New station template" };

export default function Page() {
  return (
    <Suspense fallback={null}>
      <StationTemplateNewScreen />
    </Suspense>
  );
}
