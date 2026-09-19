"use client";

import Link from "next/link";
import { Suspense, useCallback, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Alert, Button, Card, Input, Spinner } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { login } from "@/foundation/platform-client";
import { useSession } from "@/foundation/session";

/**
 * One sign-in, for every product.
 *
 * The old system had five login pages — consumer, institution, partner,
 * practice and the staff console — and which one you used decided which
 * workspace you landed in. Here identity is one table and one token, so the
 * landing is chosen from memberships after the fact.
 */
export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const { refresh } = useSession();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setBusy(true);
      setError(null);
      try {
        await login(email, password);
        await refresh();
        router.replace(params.get("next") || "/");
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
      }
    },
    [email, password, refresh, router, params],
  );

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <Card title="Sign in" className="w-full max-w-sm">
        <form onSubmit={submit} className="flex flex-col gap-4">
          {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <Input
            label="Password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <Button type="submit" disabled={busy}>
            {busy ? <Spinner label="Signing in" /> : "Sign in"}
          </Button>
          <p className="text-center text-sm text-ink-muted">
            No account?{" "}
            <Link href="/register" className="text-accent hover:underline">
              Create one
            </Link>
          </p>
        </form>
      </Card>
    </main>
  );
}
