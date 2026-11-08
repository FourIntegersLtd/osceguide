"use client";

import { useCallback, useMemo, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { LuBuilding2, LuCheck, LuChevronsUpDown, LuShield, LuUser } from "react-icons/lu";
import { useToast } from "@/foundation/hooks";
import { cn, Spinner } from "@/foundation/ui";
import { can, useSession } from "@/foundation/session";
import { isPersonal, type Workspace } from "@/foundation/routing";
import { workspacesFor } from "@/surfaces/resolveWorkspace";
import {
  CONSOLE_TARGET,
  PLATFORM_CONSOLE_NAME,
  currentTargetKey,
  workspaceTarget,
  type SwitchTarget,
} from "@/surfaces/switcherTargets";

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
 *
 * Platform staff get one more place to stand: the console at `/staff`. It is
 * offered from `can(session, "administer_platform")` (the server's answer, and
 * the same gate the staff layout applies), so nobody else is shown it.
 */
export function WorkspaceSwitcher({
  current,
  detail,
}: {
  /** `null` is the platform console, which is not an organisation. */
  current: Workspace | null;
  /** A second line under the name, e.g. the exam being practised for. */
  detail?: string | null;
}) {
  const { session, selectWorkspace } = useSession();
  const router = useRouter();
  const toast = useToast();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);

  // The same gate as the staff layout and `/app`, so they can never disagree.
  const platform = can(session, "administer_platform");
  const workspaces = useMemo(() => workspacesFor(session?.user ?? null), [session?.user]);

  const currentKey = currentTargetKey(current);
  const currentName = current?.name ?? PLATFORM_CONSOLE_NAME;

  const choose = useCallback(
    async (target: SwitchTarget) => {
      setOpen(false);
      if (target.key === currentKey) return;
      setBusy(target.key);
      try {
        await selectWorkspace(target.orgSlug);
        router.push(target.href);
      } catch {
        toast.error("Could not switch workspace", "Nothing has changed. Try again.");
      } finally {
        setBusy(null);
      }
    },
    [currentKey, selectWorkspace, router, toast],
  );

  // One workspace is not a choice. Showing a menu with a single item in it
  // invites people to look for something that is not there.
  const label = (
    <span className="min-w-0 flex-1 text-left">
      <span className="block truncate text-[13.5px] font-semibold leading-[18px] text-osce-ink-900">
        {currentName}
      </span>
      {detail ? (
        <span className="block truncate text-osce-caption font-normal text-b2c-text-muted">{detail}</span>
      ) : null}
    </span>
  );

  // With nothing to switch to, the phone drawer leaves it out: the top bar
  // already names the product and the foot already names the exam.
  if (workspaces.length + (platform ? 1 : 0) < 2) {
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
            {workspaces.map((workspace) => {
              const target = workspaceTarget(workspace);
              return (
                <SwitcherRow
                  key={target.key}
                  icon={<WorkspaceIcon workspace={workspace} />}
                  name={workspace.name}
                  active={target.key === currentKey}
                  onSelect={() => void choose(target)}
                />
              );
            })}
            {platform ? (
              <SwitcherRow
                key={CONSOLE_TARGET.key}
                icon={<LuShield className="h-4 w-4 shrink-0 text-ink-subtle" aria-hidden />}
                name={PLATFORM_CONSOLE_NAME}
                active={currentKey === CONSOLE_TARGET.key}
                onSelect={() => void choose(CONSOLE_TARGET)}
              />
            ) : null}
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

function SwitcherRow({
  icon,
  name,
  active,
  onSelect,
}: {
  icon: ReactNode;
  name: string;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        role="menuitem"
        onClick={onSelect}
        className={cn(
          "flex min-h-10 w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-surface-raised",
          active ? "text-ink" : "text-ink-muted",
        )}
      >
        {icon}
        <span className="min-w-0 flex-1 truncate">{name}</span>
        {active && <LuCheck className="h-4 w-4 shrink-0 text-accent" aria-hidden />}
      </button>
    </li>
  );
}
