import type { Metadata } from "next";

export const SITE_URL = "https://osceguide.com";

/**
 * The document head, for every page that does not override it.
 *
 * This is the retiring client's `app/metadata.ts`, ported rather than rewritten.
 * One line was deliberately *not* carried across: `manifest: "/manifest.json"`,
 * because `frontend/public/manifest.json` has never existed. The web manifest
 * comes from `app/manifest.ts`, which Next links on its own; it gives a saved
 * home-screen shortcut its icon.
 *
 * The service worker was not carried across either: `frontend/public/
 * sw.js` registers `install` and `activate` handlers that log, with every line
 * of push handling commented out, and `web-push` was never adopted here. There
 * is no PWA in the old product to port — there is a `console.log` — and push
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
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, "max-image-preview": "large" },
  },
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
    statusBarStyle: "black-translucent",
  },
};
