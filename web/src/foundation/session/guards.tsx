"use client";

import { useEffect } from "react";
import type { ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Spinner } from "@/foundation/ui";
import { loginHref } from "@/foundation/session/loginHref";
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

/**
 * Everything behind a login.
 *
 * Two people are sent somewhere else before they see the page they asked for:
 * an anonymous visitor, who goes to sign in and comes back, and an account the
 * backend has flagged `must_change_password` — one created by an invitation,
 * still holding a password somebody else set. The second is not a
 * convenience. Until it is changed, an administrator knows the credentials and
 * nothing in the product says otherwise, so the flag has to gate the whole
 * surface rather than sit unread on `/me` as it did in the first cut of this
 * port.
 *
 * `change-password` is not under this guard, which is what stops the redirect
 * from looping: it is the one place a flagged account is allowed to be.
 */
export function RequireSession({ children }: { children: ReactNode }) {
  const { status, ready, session, sessionExpired } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const mustChange = session?.user.must_change_password === true;

  useEffect(() => {
    if (!ready) return;
    const next = encodeURIComponent(pathname ?? "/");
    if (status === "anonymous") {
      router.replace(loginHref(pathname ?? "/", sessionExpired));
      return;
    }
    if (mustChange) {
      router.replace(`/change-password?next=${next}`);
    }
  }, [ready, status, sessionExpired, mustChange, pathname, router]);

  if (!ready || status === "loading") return <Resolving />;
  if (status === "anonymous") return <Resolving />;
  // Render nothing while the redirect above is in flight. A page that paints
  // for one frame is a page whose data somebody has already read off the screen.
  if (mustChange) return <Resolving />;
  return <>{children}</>;
}

/**
 * Sign-in and registration, for whoever has neither yet.
 *
 * A visitor who is already signed in and opens `/login` or `/register` used
 * to see the form anyway — register would mint a second account and silently
 * overwrite the stored session with it. This is the other half of
 * `RequireSession`: instead of sending an anonymous visitor to sign in, it
 * sends a signed-in one on to their workspace.
 */
export function RequireAnonymous({ children }: { children: ReactNode }) {
  const { status, ready } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (ready && status === "authenticated") router.replace("/app");
  }, [ready, status, router]);

  if (ready && status === "authenticated") return <Resolving />;
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
