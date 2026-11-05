import type { Metadata } from "next";
import { Suspense } from "react";
import { RubricStartScreen } from "@/capabilities/authoring/rubrics/RubricStartScreen";

export const metadata: Metadata = { title: "New marking scheme" };

export default function Page() {
  return <Suspense fallback={null}>
        <RubricStartScreen />
      </Suspense>;
}
