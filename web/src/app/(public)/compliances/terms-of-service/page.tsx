import type { Metadata } from "next";
import { TermsOfServiceContent } from "@/domains/marketing";

export const metadata: Metadata = {
  title: "Terms of service",
  description: "The terms that apply to using OSCE Guide.",
};

export default function TermsOfServicePage() {
  return <TermsOfServiceContent />;
}
