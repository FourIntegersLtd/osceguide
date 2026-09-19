import type { Metadata } from "next";
import { InstitutionsLandingPage } from "@/domains/marketing";

export const metadata: Metadata = {
  title: "For institutions",
  description:
    "Run OSCE circuits for your cohort, mark alongside the machine, and release results when they are signed off.",
};

export default function Page() {
  return <InstitutionsLandingPage />;
}
