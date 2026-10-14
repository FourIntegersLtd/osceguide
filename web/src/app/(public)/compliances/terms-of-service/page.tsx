import type { Metadata } from "next";
import { publicPageMetadata } from "@/app/metadata";
import { TermsOfServiceContent } from "@/domains/marketing";

export const metadata: Metadata = publicPageMetadata({
  path: "/compliances/terms-of-service",
  title: "Terms of service",
  description: "The terms that apply to using OSCE Guide.",
});

export default function TermsOfServicePage() {
  return <TermsOfServiceContent />;
}
