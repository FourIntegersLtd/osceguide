import type { Metadata } from "next";
import { Ops } from "@/domains/platform";

export const metadata: Metadata = { title: "Machinery" };

export default function Page() {
  return <Ops />;
}
