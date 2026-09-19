"use client";

import { useEffect } from "react";
import type { ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Spinner } from "@/foundation/ui";
import { useSession } from "@/foundation/session/SessionProvider";
import { can } from "@/foundation/session/types";
import type { Permission } from "@/foundation/session/permissions";

function Resolving() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <Spinner label="Checking your session" />
    </div>
  );
}

/** Everything behind a login. Sends anonymous visitors to sign in, and back afterwards. */
export function RequireSession({ children }: { children: ReactNode }) {
  const { status, ready } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (ready && status === "anonymous") {
      const next = encodeURIComponent(pathname ?? "/");
      router.replace(`/login?next=${next}`);
    }
  }, [ready, status, pathname, router]);

  if (!ready || status === "loading") return <Resolving />;
  if (status === "anonymous") return <Resolving />;
  return <>{children}</>;
}

/**
 * A screen the backend must permit.
 *
 * The permission string is the backend's, checked against `/me/capabilities`.
 * The frontend never derives one from a role, which is what let the old
 * institution client show an action the API then refused.
 */
export function RequireCapability({
  permission,
  children,
  fallback,
}: {
  permission: Permission;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { session, ready, status } = useSession();
  if (!ready || status === "loading") return <Resolving />;
  if (!can(session, permission)) {
    return (
      fallback ?? (
        <div className="rounded-panel border border-border bg-surface px-5 py-8 text-center">
          <p className="text-sm font-semibold text-ink">You do not have access to this</p>
          <p className="mt-1 text-sm text-ink-muted">
            Ask an administrator in your organisation if you think this is wrong.
          </p>
        </div>
      )
    );
  }
  return <>{children}</>;
}
