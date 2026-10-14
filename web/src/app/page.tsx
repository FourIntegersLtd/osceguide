import type { Metadata } from "next";
import { LandingPage } from "@/domains/marketing";
import { publicPageMetadata } from "@/app/metadata";

export const metadata: Metadata = publicPageMetadata({
  path: "/",
  // Same level as the root layout, so its `title.template` does not apply: say it in full.
  title: "OSCE Guide - AI patient simulator for OSCE, SCA, PLAB 2 and CASC practice",
  description:
    "OSCE Guide's AI platform simulates real patient interactions, helping doctors sharpen their clinical skills and enhance communication.",
});

/**
 * The public front door, rendered on the server so a crawler gets the whole
 * landing rather than a spinner.
 *
 * Somebody already signed in is sent to `/app` by `middleware.ts`, on the
 * session cookie, before this renders: `/app` decides which workspace from
 * where they were last rather than from which link they followed (ADR 0002).
 */
export default function Home() {
  return <LandingPage />;
}
