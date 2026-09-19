import type { Metadata } from "next";
import { Mocks } from "@/domains/train";

export const metadata: Metadata = { title: "Mocks" };

export default function MocksPage() {
  return <Mocks />;
}
