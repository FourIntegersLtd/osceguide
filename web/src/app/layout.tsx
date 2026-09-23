import type { Viewport } from "next";
import type { ReactNode } from "react";
import { Archivo, IBM_Plex_Mono, Inter } from "next/font/google";
import { SessionProvider } from "@/foundation/session";
import { ToastHost } from "@/foundation/ui";
import { AnalyticsConsentGate } from "@/foundation/analytics/AnalyticsConsentGate";
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

const bodyClassName = [
  inter.variable,
  archivo.variable,
  ibmPlexMono.variable,
  "font-sans",
  "antialiased",
].join(" ");

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
    <html lang="en-GB">
      <body className={bodyClassName}>
        <SessionProvider>
          {/*
            One toast stack for the whole app. At the root rather than per
            shell because a toast outlives the screen that raised it: "results
            released" has to survive the navigation that follows it.
          */}
          <ToastHost>
            <AnalyticsConsentGate>{children}</AnalyticsConsentGate>
          </ToastHost>
        </SessionProvider>
      </body>
    </html>
  );
}
