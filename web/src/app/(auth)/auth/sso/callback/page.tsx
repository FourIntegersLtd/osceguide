import type { Metadata } from "next";
import { Suspense } from "react";
import { SsoCallback } from "@/capabilities/account/SsoCallback";

export const metadata: Metadata = { title: "Signing you in" };

/**
 * The broker's return address, spelled exactly:
 * `POST /auth/sso/login` tells the identity provider to come back to
 * `{frontend_url}/auth/sso/callback`, so the URL is a contract with a system
 * outside this repository and cannot be renamed to suit the routing grammar.
 *
 * It sits inside the `(auth)` group for the layout — this is a page belonging to
 * nobody's workspace — while keeping the literal `auth` segment the broker
 * expects.
 */
export default function Page() {
  // Reads the token off the query string, so it needs a boundary.
  return (
    <Suspense fallback={null}>
      <SsoCallback />
    </Suspense>
  );
}
