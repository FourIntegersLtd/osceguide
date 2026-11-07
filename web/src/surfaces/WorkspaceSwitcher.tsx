"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { LuBuilding2, LuCheck, LuChevronsUpDown, LuUser } from "react-icons/lu";
import { cn, Spinner } from "@/foundation/ui";
import { useSession } from "@/foundation/session";
import { isPersonal, workspaceBasePath, type Workspace } from "@/foundation/routing";
import { workspacesFor } from "@/surfaces/resolveWorkspace";
import { switcherGroups } from "@/surfaces/switcherGroups";

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
export function WorkspaceSwitcher({
  current,
  detail,
}: {
  current: Workspace;
  /** A second line under the name, e.g. the exam being practised for. */
  detail?: string | null;
}) {
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
  const label = (
    <span className="min-w-0 flex-1 text-left">
      <span className="block truncate text-[13.5px] font-semibold leading-[18px] text-osce-ink-900">
        {current.name}
      </span>
      {detail ? (
        <span className="block truncate text-osce-caption font-normal text-b2c-text-muted">{detail}</span>
      ) : null}
    </span>
  );

  // With nothing to switch to, the phone drawer leaves it out: the top bar
  // already names the product and the foot already names the exam.
  if (workspaces.length < 2) {
    return <div className="hidden min-h-11 items-center px-2.5 lg:flex">{label}</div>;
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-haspopup="menu"
        className="flex min-h-11 w-full items-center gap-2 rounded-osce-md px-2.5 text-left hover:bg-osce-navActive"
      >
        {label}
        {busy ? (
          <Spinner className="text-current" />
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
            className="absolute left-0 right-0 z-50 mt-1 max-h-[60dvh] overflow-y-auto rounded-panel border border-border bg-surface py-1 shadow-lg"
          >
            {switcherGroups(workspaces).map((group) => (
              <li key={group.label ?? "workspaces"} role="none">
                {group.label ? (
                  <div className="px-3 pb-1 pt-2 text-osce-caption font-semibold uppercase text-b2c-text-muted">{group.label}</div>
                ) : null}
                <ul role="group" aria-label={group.label ?? undefined}>
                  {group.items.map((workspace) => {
                    const active = workspace.slug === current.slug;
                    return (
                      <li key={workspace.slug} role="none">
                        <button
                          type="button"
                          role="menuitem"
                          onClick={() => void choose(workspace)}
                          className={cn(
                            "flex min-h-10 w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-surface-raised",
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
              </li>
            ))}
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
