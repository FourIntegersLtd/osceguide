import type { Metadata } from "next";
import { SITE_URL, isProductionSiteUrl } from "@/foundation/config/siteUrl";

// Re-exported so the existing importers (`app/robots.ts`, `app/sitemap.ts`)
// keep reading it from here; the literal value itself lives in exactly one
// place, `foundation/config/siteUrl.ts`.
export { SITE_URL };

/**
 * The `robots` field for a given site URL: full indexing on production,
 * noindex/nofollow everywhere else (staging, a Vercel preview). Staging and
 * every preview build with `NODE_ENV=production` too, so this is decided from
 * the site URL (see `foundation/config/siteUrl.ts`) rather than the
 * environment. Exported as a pure function — taking the site URL as an
 * argument rather than reading the module-level `SITE_URL` — so a test can
 * assert both branches with literal values, without mutating `process.env`.
 */
export function metadataRobotsFor(siteUrl: string): NonNullable<Metadata["robots"]> {
  if (!isProductionSiteUrl(siteUrl)) {
    return { index: false, follow: false, googleBot: { index: false, follow: false } };
  }
  return {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  };
}

/**
 * The document head, for every page that does not override it.
 *
 * This is the retiring client's `app/metadata.ts`, ported rather than rewritten.
 * One line was deliberately *not* carried across: `manifest: "/manifest.json"`,
 * because `frontend/public/manifest.json` has never existed. The web manifest
 * comes from `app/manifest.ts`, which Next links on its own; it gives a saved
 * home-screen shortcut its icon.
 *
 * The retiring client's service worker was not carried across: it logged on
 * `install` and `activate` and had every line of push handling commented out.
 * `public/sw.js` here is new and serves only the offline page; push
 * notifications remain the open product decision the gap register says they are.
 *
 * `metadataBase` is the load-bearing one. Without it, every relative `url` and
 * every relative image path below resolves against the request origin at
 * render time, which is how a shared link ends up pointing at `localhost:3100`.
 */
export const metadata: Metadata = {
  title: {
    template: "%s | OSCE Guide",
    default: "OSCE Guide - Master your Clinical Simulation Exams with confidence",
  },
  description:
    "OSCE Guide's AI platform simulates real patient interactions, helping doctors sharpen their clinical skills and enhance communication.",
  keywords: [
    "osce guide",
    "osceguide",
    "osceguide.com",
    "osce guide ai",
    "RCGP SCA exam",
    "RCPsych CASC exam",
    "GMC PLAB 2 exam",
    "OSCE preparation",
    "clinical assessment training",
    "medical examination practice",
    "AI medical training",
    "GP exam preparation",
    "Psychiatry exam preparation",
    "PLAB preparation",
    "simulated clinical scenarios",
    "voice AI medical training",
    "RCGP exam guide",
    "CASC exam guide",
    "PLAB 2 exam guide",
    "clinical skills assessment",
    "your ai patient that never gets tired",
    "MRCGP exam preparation",
    "CASC practice cases",
    "PLAB 2 practice cases",
    "SCA practice cases",
    "GP training scenarios",
    "Psychiatry training scenarios",
    "medical consultation skills",
    "clinical communication practice",
    "structured clinical assessment",
  ],
  authors: [{ name: "OSCE Guide", url: SITE_URL }],
  metadataBase: new URL(SITE_URL),
  creator: "OSCE Guide",
  publisher: "OSCE Guide",
  // Staging and Vercel previews must never advertise themselves to a crawler
  // or an AI bot as if they were the indexable site — only production may.
  robots: metadataRobotsFor(SITE_URL),
  alternates: {
    canonical: SITE_URL,
    languages: { "en-GB": SITE_URL },
  },
  openGraph: {
    type: "website",
    locale: "en_GB",
    url: SITE_URL,
    siteName: "OSCE Guide",
    title: "OSCE Guide - Master your Clinical Simulation Exams with confidence",
    description:
      "OSCE Guide's AI platform simulates real patient interactions, helping doctors sharpen their clinical skills and enhance communication.",
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: "OSCE Guide - AI Patient Simulator",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    site: "@osceguide",
    creator: "@osceguide",
    title: "OSCE Guide - Master your Clinical Simulation Exams with confidence",
    description:
      "OSCE Guide's AI platform simulates real patient interactions, helping doctors sharpen their clinical skills and enhance communication.",
    images: ["/twitter-image.png"],
  },
  appleWebApp: {
    capable: true,
    title: "OSCE Guide",
    // Not "black-translucent": that draws the page underneath the status bar
    // with white clock text, so every fixed top bar collided with it and the
    // text vanished on the light skin. "default" keeps the page below the bar.
    statusBarStyle: "default",
  },
  // iOS otherwise turns any run of digits (a dose, a score) into a phone link.
  formatDetection: { telephone: false },
};
