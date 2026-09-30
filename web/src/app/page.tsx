"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@/foundation/ui";
import { useSession } from "@/foundation/session";
import { LandingPage } from "@/domains/marketing";

/**
 * The public front door.
 *
 * Marketing owns the root, and a visitor with no session sees the landing.
 * Somebody already signed in is sent to `/app`, which decides which workspace
 * from where they were last rather than from which link they followed.
 *
 * That split is ADR 0002: the old front door chose a *product arm* here, from
 * memberships, and always chose an organisation — which is why a doctor who
 * belonged to a trust could not reach their own practice at all.
 */
export default function Home() {
  const { status, ready } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (ready && status === "authenticated") router.replace("/app");
  }, [ready, status, router]);

  if (!ready || status === "authenticated") {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <Spinner label="Loading" />
      </main>
    );
  }

  return <LandingPage />;
}
