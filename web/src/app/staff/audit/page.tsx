import type { Metadata } from "next";
import { PlatformAudit } from "@/domains/platform";

export const metadata: Metadata = { title: "Audit log" };

export default function Page() {
  return <PlatformAudit />;
}
