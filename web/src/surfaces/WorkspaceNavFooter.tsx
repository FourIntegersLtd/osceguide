"use client";

import Link from "next/link";
import { LuLogOut } from "react-icons/lu";
import { PiSparkle } from "react-icons/pi";
import { cn } from "@/foundation/ui";
import { b2cIconButton, b2cNavUpgradeButton } from "@/foundation/ui/productTokens";
import { PERSONAL_WORKSPACE, workspaceBasePath } from "@/foundation/routing";
import { isPlatformAdmin, useCurrentExam, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";
import { holdsPaidAccess } from "@/capabilities/account/access";
import { listEntitlements } from "@/capabilities/account/api";
import { useAsync } from "@/foundation/hooks";

/**
 * The foot of the workspace sidebar (canvas `train-dashboard`): who you are
 * with sign-out beside your name. A consumer also gets the upgrade button
 * until they hold paid access to their current exam (the rule the payments
 * tab uses), and the exam countdown.
 */
export function WorkspaceNavFooter({
  consumer,
  staff = false,
  collapsed = false,
}: {
  consumer: boolean;
  staff?: boolean;
  collapsed?: boolean;
}) {
  const { session, signOut } = useSession();
  const { hrefFor } = useSurface();
  const { codes, code, setCode } = useCurrentExam();
  const userId = session?.user.id ?? null;
  // Not a gate, so a failed read hides the button rather than an error.
  const entitlements = useAsync(
    async (signal) => (consumer && userId ? (await listEntitlements(signal)).items : null),
    [consumer, userId],
  );

  const name = session?.user.name || session?.user.email || "Account";
  const email = session?.user.name ? session.user.email : null;
  const meta = consumer ? examMeta(code, session?.user.exam_date ?? null) : null;
  // `codes` is the exam the account was opened for plus any grants, so it is
  // not evidence of payment; only a paid entitlement is.
  const showUpgrade =
    consumer && entitlements.data !== null && !holdsPaidAccess(entitlements.data, code);

  const upgrade = showUpgrade ? (
    <Link
      href={`${hrefFor("/settings")}?tab=payments`}
      className={cn(b2cNavUpgradeButton, collapsed && "h-11 !px-0")}
      title="Upgrade to Pro"
      aria-label={collapsed ? "Upgrade to Pro" : undefined}
    >
      <PiSparkle className="h-4 w-4 shrink-0" aria-hidden />
      <span className={collapsed ? "sr-only" : undefined}>Upgrade to Pro</span>
    </Link>
  ) : null;

  const signOutButton = (
    <button
      type="button"
      onClick={() => void signOut()}
      aria-label="Sign out"
      title="Sign out"
      className={cn(b2cIconButton, "sm:h-[30px] sm:w-[30px]")}
    >
      <LuLogOut className="h-4 w-4" aria-hidden />
    </button>
  );

  if (collapsed) {
    return (
      <div className="mt-auto flex shrink-0 flex-col items-center gap-2 border-t border-b2c-border px-1.5 py-3">
        {upgrade}
        {signOutButton}
      </div>
    );
  }

  return (
    <div className="mt-auto shrink-0 px-3 pb-3.5">
      {upgrade ? <div className="mb-3">{upgrade}</div> : null}

      {consumer && codes.length > 1 ? (
        <label className="block px-3 py-2">
          <span className="sr-only">Exam</span>
          <select
            value={code ?? ""}
            onChange={(event) => setCode(event.target.value)}
            className="w-full bg-transparent text-osce-meta font-medium text-osce-ink-900"
          >
            {codes.map((item) => (
              <option key={item} value={item}>
                {examMeta(item, item === code ? session?.user.exam_date ?? null : null)}
              </option>
            ))}
          </select>
        </label>
      ) : meta ? (
        <p className="px-3 py-2 text-osce-meta font-medium text-osce-ink-900">{meta}</p>
      ) : null}

      {staff ? (
        <Link
          href={workspaceBasePath(PERSONAL_WORKSPACE)}
          className="block px-3 pb-2 text-osce-meta font-medium text-osce-accent hover:text-osce-accent-hover"
        >
          My practice
        </Link>
      ) : isPlatformAdmin(session) ? (
        <Link
          href="/staff"
          className="block px-3 pb-2 text-osce-meta font-medium text-osce-accent hover:text-osce-accent-hover"
        >
          Staff console
        </Link>
      ) : null}

      <div className="mt-2 flex items-center gap-2 border-t border-b2c-border pl-2.5 pr-1.5 pt-2.5">
        <span className="flex min-w-0 flex-1 items-center gap-2.5">
          <span
            aria-hidden
            className="flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full bg-osce-navActive text-[11.5px] font-semibold text-osce-ink-700"
          >
            {initials(name)}
          </span>
          <span className="min-w-0">
            <span className="block truncate font-medium leading-[19px] text-osce-ink-900">{name}</span>
            {email ? (
              <span className="block truncate text-osce-meta text-b2c-text-muted">{email}</span>
            ) : null}
          </span>
        </span>
        {signOutButton}
      </div>
    </div>
  );
}

function initials(name: string): string {
  const words = name.replace(/@.*/, "").split(/[\s._-]+/).filter(Boolean);
  const first = words[0] ?? "?";
  const last = words.length > 1 ? words[words.length - 1] : undefined;
  const letters = last ? first.charAt(0) + last.charAt(0) : first.slice(0, 2);
  return letters.toUpperCase();
}

function examMeta(code: string | null, examDate: string | null): string | null {
  if (!code) return null;
  const label = code.toUpperCase();
  if (!examDate) return label;

  const exam = new Date(`${examDate}T00:00:00`);
  if (Number.isNaN(exam.getTime())) return label;

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const days = Math.round((exam.getTime() - today.getTime()) / 86_400_000);

  if (days < 0) return `${label} · exam passed`;
  if (days === 0) return `${label} · exam today`;
  if (days < 7) return `${label} · ${days} ${days === 1 ? "day" : "days"} to exam`;
  const weeks = Math.round(days / 7);
  return `${label} · ${weeks} ${weeks === 1 ? "week" : "weeks"} to exam`;
}
