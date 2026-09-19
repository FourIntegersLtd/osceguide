"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { LuBuilding2, LuCheck, LuChevronsUpDown, LuUser } from "react-icons/lu";
import { cn, Spinner } from "@/foundation/ui";
import { useSession } from "@/foundation/session";
import { isPersonal, workspaceBasePath, type Workspace } from "@/foundation/routing";
import { workspacesFor } from "@/surfaces/resolveWorkspace";

/**
 * Moving between your own practice and the organisations you belong to.
 *
 * This is the piece whose absence made the app look like it had lost its
 * consumer half: the front door sent anybody with a membership straight to
 * their institution, and no screen offered a way back. A doctor who practises
 * on their own *and* sits their trust's mock exams is one person with two
 * workspaces, and this is where they say which one they are in.
 *
 * Switching re-mints the token, so the choice is carried by the token rather
 * than by a value in the URL. A stale tab cannot then act in a workspace the
 * person has left.
 */
export function WorkspaceSwitcher({ current }: { current: Workspace }) {
  const { session, selectWorkspace } = useSession();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  const workspaces = useMemo(() => workspacesFor(session?.user ?? null), [session?.user]);

  const choose = useCallback(
    async (workspace: Workspace) => {
      setOpen(false);
      if (workspace.slug === current.slug) return;
      setBusy(workspace.slug);
      try {
        await selectWorkspace(workspace.orgSlug);
        router.push(workspaceBasePath(workspace));
      } finally {
        setBusy(null);
      }
    },
    [current.slug, selectWorkspace, router],
  );

  // One workspace is not a choice. Showing a menu with a single item in it
  // invites people to look for something that is not there.
  if (workspaces.length < 2) {
    return <span className="truncate text-sm font-semibold text-ink">{current.name}</span>;
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="flex w-full items-center gap-2 rounded-control px-2 py-1.5 text-left hover:bg-surface-raised"
      >
        <WorkspaceIcon workspace={current} />
        <span className="min-w-0 flex-1 truncate text-sm font-semibold text-ink">
          {current.name}
        </span>
        {busy ? (
          <Spinner />
        ) : (
          <LuChevronsUpDown className="h-4 w-4 shrink-0 text-ink-subtle" aria-hidden />
        )}
      </button>

      {open && (
        <>
          {/* Clicking anywhere else closes it, including on touch. */}
          <button
            type="button"
            aria-hidden
            tabIndex={-1}
            className="fixed inset-0 z-40 cursor-default"
            onClick={() => setOpen(false)}
          />
          <ul
            role="menu"
            className="absolute left-0 right-0 z-50 mt-1 overflow-hidden rounded-panel border border-border bg-surface py-1 shadow-lg"
          >
            {workspaces.map((workspace) => {
              const active = workspace.slug === current.slug;
              return (
                <li key={workspace.slug}>
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => void choose(workspace)}
                    className={cn(
                      "flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-surface-raised",
                      active ? "text-ink" : "text-ink-muted",
                    )}
                  >
                    <WorkspaceIcon workspace={workspace} />
                    <span className="min-w-0 flex-1 truncate">{workspace.name}</span>
                    {active && <LuCheck className="h-4 w-4 shrink-0 text-accent" aria-hidden />}
                  </button>
                </li>
              );
            })}
          </ul>
        </>
      )}
    </div>
  );
}

function WorkspaceIcon({ workspace }: { workspace: Workspace }) {
  const Icon = isPersonal(workspace) ? LuUser : LuBuilding2;
  return <Icon className="h-4 w-4 shrink-0 text-ink-subtle" aria-hidden />;
}
