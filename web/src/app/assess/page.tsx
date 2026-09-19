"use client";

import Link from "next/link";
import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { LuArrowRight, LuBuilding2 } from "react-icons/lu";
import { Alert, Card, EmptyState, PageHeader, Spinner } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { RequireSession, useSession } from "@/foundation/session";

/**
 * Which workspace, when somebody belongs to more than one.
 *
 * Switching re-mints the token with the new membership active, so the choice is
 * carried by the token rather than by a value in the URL. A stale tab cannot
 * then act in a workspace the person has left.
 */
export default function WorkspacePickerPage() {
  return (
    <RequireSession>
      <Picker />
    </RequireSession>
  );
}

function Picker() {
  const { session, selectWorkspace } = useSession();
  const router = useRouter();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);

  const choose = useCallback(
    async (slug: string) => {
      setBusy(slug);
      setError(null);
      try {
        await selectWorkspace(slug);
        router.push(`/assess/${slug}`);
      } catch (cause) {
        setError(cause instanceof Error ? cause : new Error(String(cause)));
        setBusy(null);
      }
    },
    [selectWorkspace, router],
  );

  const memberships = session?.user.memberships ?? [];

  return (
    <main className="mx-auto w-full max-w-2xl px-4 py-12">
      <PageHeader title="Choose a workspace" description="You belong to more than one." />

      {error && (
        <Alert tone="danger" className="mt-4">
          {errorMessage(error)}
        </Alert>
      )}

      <div className="mt-6 flex flex-col gap-2">
        {memberships.length === 0 ? (
          <EmptyState
            title="You are not in an organisation"
            description="Your own practice is on the home screen."
            action={
              <Link href="/" className="text-sm text-accent hover:underline">
                Go to practice
              </Link>
            }
          />
        ) : (
          memberships.map((membership) => (
            <button
              key={membership.org_slug}
              type="button"
              onClick={() => void choose(membership.org_slug)}
              disabled={busy !== null}
              className="w-full text-left"
            >
              <Card className="transition-colors hover:border-border-strong">
                <div className="flex items-center justify-between gap-3">
                  <span className="flex min-w-0 items-center gap-3">
                    <LuBuilding2 className="h-4 w-4 shrink-0 text-ink-subtle" aria-hidden />
                    <span className="min-w-0">
                      <span className="block truncate text-sm font-medium text-ink">
                        {membership.org_name ?? membership.org_slug}
                      </span>
                      <span className="text-xs capitalize text-ink-subtle">{membership.role}</span>
                    </span>
                  </span>
                  {busy === membership.org_slug ? (
                    <Spinner />
                  ) : (
                    <LuArrowRight className="h-4 w-4 text-ink-subtle" aria-hidden />
                  )}
                </div>
              </Card>
            </button>
          ))
        )}
      </div>

      <p className="mt-6 text-sm text-ink-muted">
        Rostered onto a sitting?{" "}
        <Link href="/assess/trainee" className="text-accent hover:underline">
          Go to my training
        </Link>
      </p>
    </main>
  );
}
