"use client";

import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Alert, Button, PageSpinner } from "@/foundation/ui";
import { loginHref } from "@/foundation/session/loginHref";
import { lastSessionUser, nextAfterSignIn } from "@/foundation/session/sessionUser";
import { useSession } from "@/foundation/session/SessionProvider";
import { can } from "@/foundation/session/types";
import type { Permission } from "@/foundation/session/permissions";

function Resolving() {
  return (
    <PageSpinner label="Checking your session" fill="section" />
  );
}

/**
 * The session could not be checked (a gateway error, the network), so neither
 * the page nor a sign-in redirect is the honest answer. The provider keeps
 * asking in the background; the button asks now.
 */
function Unavailable({ retry }: { retry: () => Promise<unknown> }) {
  return (
    <div className="mx-auto max-w-md px-4 py-16">
      <Alert tone="danger" title="We could not check your session">
        <p>The server did not answer. It is asked again on its own, or you can try now.</p>
        <Button variant="secondary" size="sm" className="mt-3" onClick={() => retry()}>
          Try again
        </Button>
      </Alert>
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
 * `change-password` passes `allowMustChange`, which is what stops the
 * redirect from looping: it is the one place a flagged account is allowed to
 * be. It is still behind the login: a signed-out visitor used to get
 * the form and a refusal for a request that could never succeed.
 */
export function RequireSession({
  children,
  allowMustChange = false,
}: {
  children: ReactNode;
  allowMustChange?: boolean;
}) {
  const { status, ready, session, sessionExpired, signedOutTo, unavailable, refresh } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const mustChange = !allowMustChange && session?.user.must_change_password === true;

  useEffect(() => {
    if (!ready) return;
    const next = encodeURIComponent(pathname ?? "/");
    if (status === "anonymous") {
      router.replace(signedOutTo ?? loginHref(pathname ?? "/", sessionExpired));
      return;
    }
    if (mustChange) {
      router.replace(`/change-password?next=${next}`);
    }
  }, [ready, status, sessionExpired, signedOutTo, mustChange, pathname, router]);

  if (unavailable) return <Unavailable retry={refresh} />;
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
  const { status, ready, session } = useSession();
  const router = useRouter();
  // Who held this tab's session when the form opened, before a sign-in here replaces it.
  const [previousUser] = useState(lastSessionUser);
  // Where `/login?next=` was heading, if it was this person's: go there rather than to the picker.
  const params = useSearchParams();
  const userId = session?.user.id ?? null;
  const next = userId ? nextAfterSignIn(params, previousUser, userId) : null;

  useEffect(() => {
    if (ready && status === "authenticated") router.replace(next ?? "/app");
  }, [ready, status, router, next]);

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
  const { session, ready, status, unavailable, refresh } = useSession();
  if (unavailable) return <Unavailable retry={refresh} />;
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
