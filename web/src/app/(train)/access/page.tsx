import type { Metadata } from "next";
import { Access } from "@/domains/train";

export const metadata: Metadata = { title: "Your access" };

export default function AccessPage() {
  return <Access />;
}
