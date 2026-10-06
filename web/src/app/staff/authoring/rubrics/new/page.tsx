import type { Metadata } from "next";
import { RubricStartScreen } from "@/capabilities/authoring/rubrics/RubricStartScreen";

export const metadata: Metadata = { title: "New marking scheme" };

export default function Page() {
  return <RubricStartScreen />;
}
