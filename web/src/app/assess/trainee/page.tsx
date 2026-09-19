import type { Metadata } from "next";
import { TraineeHome } from "@/domains/assess";

export const metadata: Metadata = { title: "My sittings" };

export default function TraineePage() {
  return <TraineeHome />;
}
