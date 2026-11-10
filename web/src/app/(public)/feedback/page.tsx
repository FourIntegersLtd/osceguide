import type { Metadata } from "next";
import { publicPageMetadata } from "@/app/metadata";
import { HomeFeedback } from "@/domains/marketing/home/HomeFeedback";
import { SiteShell } from "@/domains/marketing/site/SiteShell";

export const metadata: Metadata = publicPageMetadata({
  path: "/feedback",
  title: "Your feedback",
  description: "Tell OSCE Guide what you really think, or share a feature you wish existed. We read every message.",
});

export default function Page() {
  return (
    <SiteShell>
      <HomeFeedback asPageTitle />
    </SiteShell>
  );
}
