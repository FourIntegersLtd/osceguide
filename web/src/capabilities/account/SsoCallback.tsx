"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Alert, Spinner } from "@/foundation/ui";
import { useSession } from "@/foundation/session";
import { completeSsoSignIn } from "@/capabilities/account/api";
import AuthShell from "@/capabilities/account/AuthShell";
import { readSsoCallback } from "@/capabilities/account/support/ssoCallback";

/**
 * The page the identity provider sends people back to.
 *
 * `POST /auth/sso/login` hands the browser to the broker with a return address
 * of `{frontend_url}/auth/sso/callback?org_slug=…`, and the broker appends the
 * token it minted (and, for Entra, the signed `state`: `readSsoCallback`).
 * This page's whole job is to post them to
 * `POST /auth/sso/callback`, let the backend **verify** it, adopt the session
 * pair the answer carries, and get out of the way.
 *
 * It verifies rather than decodes on purpose. A token that arrives over a URL
 * is untrusted input, and reading the claims here to decide who somebody is
 * would be a way to sign in as anyone who can type a JWT; the backend checks
 * the signature against the configured issuer and provisions from *that*.
 *
 * Strict mode runs an effect twice, and the second run would post a token the
 * backend has already spent. The ref is what keeps it to one.
 *
 * It waits for the session check first. Somebody already signed in goes
 * on to `/app` with their session untouched rather than having it silently
 * replaced by whoever the token names. And the single-use token is taken out
 * of the address bar as soon as it is read, so it is not left in history and
 * a reload says the link was used instead of failing on a spent token.
 */
export function SsoCallback() {
  const params = useSearchParams();
  const router = useRouter();
  const { refresh, ready, status } = useSession();
  const started = useRef(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!ready || status === "loading" || started.current) return;
    started.current = true;

    if (status === "authenticated") {
      router.replace(`/app`);
      return;
    }
    const callback = readSsoCallback(params);
    window.history.replaceState(null, "", window.location.pathname);
    if (!callback.ok) {
      setError(callback.message);
      return;
    }

    void completeSsoSignIn(callback.orgSlug, callback.token, callback.state)
      .then(async () => {
        await refresh();
        // Into the workspace picker, which reads the memberships the callback
        // provisioned. `/app/<me>` would assume a personal account exists, and
        // an SSO person's first sign-in may have just created one.
        router.replace(`/app`);
      })
      .catch((cause: unknown) => {
        setError(
          cause instanceof Error
            ? cause.message
            : "We could not finish signing you in with your organisation.",
        );
      });
  }, [params, ready, status, refresh, router]);

  return (
    <AuthShell title="Signing you in" subtitle="Finishing with your organisation." variant="card">
      {error ? (
        <div className="space-y-4">
          <Alert tone="danger">{error}</Alert>
          <button
            type="button"
            onClick={() => router.replace(`/login`)}
            className="text-osce-data font-medium text-osce-accent underline"
          >
            Back to sign in
          </button>
        </div>
      ) : (
        <Spinner label="Signing you in" />
      )}
    </AuthShell>
  );
}
