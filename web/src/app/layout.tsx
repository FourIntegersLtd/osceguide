import type { Metadata } from "next";
import type { ReactNode } from "react";
import { SessionProvider } from "@/foundation/session";
import { ToastHost } from "@/foundation/ui";
import "@/app/globals.css";

export const metadata: Metadata = {
  title: { default: "OSCE Guide", template: "%s · OSCE Guide" },
  description: "Practise, assess and hire against real clinical scenarios.",
};

/**
 * The root, and the only place the session is resolved.
 *
 * `data-surface` is deliberately not set here: each surface shell sets its own,
 * so a route that belongs to no surface (sign-in, the workspace picker) gets
 * the default skin rather than inheriting whichever arm happened to be last.
 */
export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en-GB">
      <body>
        <SessionProvider>
          {/*
            One toast stack for the whole app. At the root rather than per
            shell because a toast outlives the screen that raised it: "results
            released" has to survive the navigation that follows it.
          */}
          <ToastHost>{children}</ToastHost>
        </SessionProvider>
      </body>
    </html>
  );
}
