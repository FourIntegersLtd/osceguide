import type { Metadata } from "next";
import { BillingQueue } from "@/domains/platform";

export const metadata: Metadata = { title: "Billing" };

export default function Page() {
  return <BillingQueue />;
}
