"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Spinner } from "@/foundation/ui";

/**
 * A screen that only sends you on: a spinner while `router.replace(to)` runs.
 * `to` is null while the destination is still being worked out.
 */
export function Redirecting({ to }: { to: string | null }) {
  const router = useRouter();
  useEffect(() => {
    if (to) router.replace(to);
  }, [to, router]);
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Spinner label="Loading" size="lg" className="text-ink-subtle" />
    </div>
  );
}
