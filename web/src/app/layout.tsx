import type { Viewport } from "next";
import type { ReactNode } from "react";
import { Archivo, IBM_Plex_Mono, Inter } from "next/font/google";
import localFont from "next/font/local";
import { SessionProvider } from "@/foundation/session";
import { ToastHost } from "@/foundation/ui";
import { AnalyticsConsentGate } from "@/foundation/analytics/AnalyticsConsentGate";
import InstallPrompt from "@/domains/marketing/InstallPrompt";
import "@/app/globals.css";

/*
 * The document head lives in `app/metadata.ts` so that the one object Next
 * reads for every page can be read on its own. Re-exported here through the
 * conventional binding.
 */
export { metadata } from "@/app/metadata";

/*
 * Three faces, as CSS variables.
 *
 * Inter for body, Archivo for headings and the wordmark, IBM Plex Mono for the
 * small uppercase captions over tables and cards. The token vocabulary and the
 * Tailwind config both name these variables — `font-landing-heading` resolves
 * to `var(--font-archivo)` — so without them loaded here every screen falls
 * back to the system stack, which is what "the font is not right" looks like.
 */
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const archivo = Archivo({
  subsets: ["latin"],
  variable: "--font-archivo",
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const ibmPlexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-ibm-plex-mono",
  weight: ["400", "500"],
  display: "swap",
});

/*
 * The train arm's faces, from the "OSCE Guide Screens v2" canvas: Open Sauce
 * Sans for everything, Fraunces for page titles only. Both OFL; the licences
 * sit beside the files. Train switches to them through `--font-ui` and
 * `--font-display` in tokens.css, so the other arms keep Inter and Archivo.
 */
const openSauceSans = localFont({
  src: [
    { path: "./fonts/OpenSauceSans-400.ttf", weight: "400", style: "normal" },
    { path: "./fonts/OpenSauceSans-500.woff2", weight: "500", style: "normal" },
    { path: "./fonts/OpenSauceSans-600.woff2", weight: "600", style: "normal" },
    { path: "./fonts/OpenSauceSans-700.woff2", weight: "700", style: "normal" },
  ],
  variable: "--font-open-sauce",
  display: "swap",
});

const fraunces = localFont({
  src: [
    { path: "./fonts/Fraunces-500.woff2", weight: "500", style: "normal" },
    { path: "./fonts/Fraunces-600.woff2", weight: "600", style: "normal" },
  ],
  variable: "--font-fraunces",
  display: "swap",
});

/*
 * The variables go on <html>, not <body>: train's `:root:has(...)` block
 * points `--font-ui` at `--font-open-sauce`, and a custom property resolves
 * its `var()` on the element that declares it.
 */
const fontVariables = [
  inter.variable,
  archivo.variable,
  ibmPlexMono.variable,
  openSauceSans.variable,
  fraunces.variable,
].join(" ");

const bodyClassName = "font-sans antialiased";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#ffffff",
};

/**
 * The root, and the only place the session is resolved.
 *
 * `data-surface` is deliberately not set here: each surface shell sets its own,
 * so a route that belongs to no surface (sign-in, the landing) gets the default
 * skin rather than inheriting whichever arm happened to be last.
 */
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en-GB" className={fontVariables}>
      <body className={bodyClassName}>
        <SessionProvider>
          {/*
            One toast stack for the whole app. At the root rather than per
            shell because a toast outlives the screen that raised it: "results
            released" has to survive the navigation that follows it.
          */}
          <ToastHost>
            <AnalyticsConsentGate>{children}</AnalyticsConsentGate>
            {/*
              The add-to-home-screen helper, on every arm — which is where the
              retiring client had it, in its one app-wide layout. It decides for
              itself whether to appear: a phone that is not mobile, a browser
              already running standalone, somebody who dismissed it, and the
              first visit where the consent question is still on screen all keep
              it away. Inside `SessionProvider` because whose account this is
              forms part of that answer.
            */}
            <InstallPrompt />
          </ToastHost>
        </SessionProvider>
      </body>
    </html>
  );
}
