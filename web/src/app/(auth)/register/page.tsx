"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { Alert, Button, Card, Input, Spinner } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { register } from "@/foundation/platform-client";
import { useSession } from "@/foundation/session";

/** Consumers sign themselves up. Institutions provision their people instead. */
export default function RegisterPage() {
  const router = useRouter();
  const { refresh } = useSession();
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const submit = useCallback(
    async (event: React.FormEvent) => {
      event.preventDefault();
      setBusy(true);
      setError(null);
      try {
        await register(form);
        await refresh();
        router.replace("/");
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
      } finally {
        setBusy(false);
      }
    },
    [form, refresh, router],
  );

  return (
    <main className="flex min-h-screen items-center justify-center bg-canvas px-4">
      <Card title="Create your account" className="w-full max-w-sm">
        <form onSubmit={submit} className="flex flex-col gap-4">
          {error && <Alert tone="danger">{errorMessage(error)}</Alert>}
          <Input
            label="Name"
            required
            value={form.name}
            onChange={(event) => setForm((f) => ({ ...f, name: event.target.value }))}
          />
          <Input
            label="Email"
            type="email"
            autoComplete="email"
            required
            value={form.email}
            onChange={(event) => setForm((f) => ({ ...f, email: event.target.value }))}
          />
          <Input
            label="Password"
            type="password"
            autoComplete="new-password"
            required
            hint="At least 12 characters."
            value={form.password}
            onChange={(event) => setForm((f) => ({ ...f, password: event.target.value }))}
          />
          <Button type="submit" disabled={busy}>
            {busy ? <Spinner label="Creating account" /> : "Create account"}
          </Button>
          <p className="text-center text-sm text-ink-muted">
            Already have one?{" "}
            <Link href="/login" className="text-accent hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </Card>
    </main>
  );
}
