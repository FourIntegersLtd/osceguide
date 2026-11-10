import type { Metadata } from "next";
import { publicPageMetadata } from "@/app/metadata";
import { HomeFounders } from "@/domains/marketing/home/HomeVoices";
import { SiteShell } from "@/domains/marketing/site/SiteShell";

export const metadata: Metadata = publicPageMetadata({
  path: "/founders",
  title: "A message from our founders",
  description: "Why Kenny and Aisha built OSCE Guide: realistic AI patients and honest feedback for doctors preparing for clinical exams.",
});

export default function Page() {
  return (
    <SiteShell>
      <HomeFounders asPageTitle />
    </SiteShell>
  );
}
