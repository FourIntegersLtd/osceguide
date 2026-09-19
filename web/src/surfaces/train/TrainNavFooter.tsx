"use client";

import Link from "next/link";
import { LuSparkles } from "react-icons/lu";
import { cn } from "@/foundation/ui";
import { useCurrentExam, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";

/**
 * What sits under the consumer navigation: upgrade, who you are, what you sit.
 *
 * All three are the retiring client's, in its order. The last line is the one
 * that matters most: `SCA · 3 weeks to exam` is how somebody confirms at a
 * glance that the whole app is showing the right exam — which used to be
 * guaranteed by the hostname and now is not.
 *
 * The upgrade button opens Settings rather than a modal of its own. The old
 * client put the plan cards in both places; there is one screen that sells a
 * subscription now, and this is a way to it.
 *
 * It is also the **only** exam switcher in the product. Four screens used to
 * carry their own dropdown, each over the full catalogue; almost nobody holds
 * two exams, so for almost everybody this is a line of text.
 */
export function TrainNavFooter() {
  const { session } = useSession();
  const { hrefFor } = useSurface();
  const { codes, code, setCode } = useCurrentExam();

  const displayName = session?.user.name || session?.user.email || "Account";
  const meta = examMeta(code, session?.user.exam_date ?? null);

  return (
    <div className="mt-auto border-t border-border px-3 py-4">
      {/*
       * Offered only to somebody with nothing live. `codes` is live access
       * plus the exam the account was opened for, so a person on their free
       * trial still sees this — which is exactly who it is for.
       */}
      {codes.length === 0 && (
        <Link
          href={`${hrefFor("/settings")}?tab=payments`}
          className={cn(
            "mb-4 flex w-full items-center justify-center gap-1.5 rounded-control px-3 py-2",
            "text-sm font-medium text-ink-inverse transition-colors",
            "bg-accent hover:bg-accent-strong",
          )}
        >
          <LuSparkles className="h-4 w-4 shrink-0" aria-hidden />
          Upgrade to Pro
        </Link>
      )}

      <p className="truncate text-sm font-medium text-ink">{displayName}</p>

      {codes.length > 1 ? (
        <label className="mt-1 block">
          <span className="sr-only">Exam</span>
          <select
            value={code ?? ""}
            onChange={(event) => setCode(event.target.value)}
            className="w-full bg-transparent font-mono text-xs uppercase tracking-wide text-ink-muted"
          >
            {codes.map((item) => (
              <option key={item} value={item}>
                {item.toUpperCase()}
              </option>
            ))}
          </select>
        </label>
      ) : meta ? (
        <p className="mt-1 font-mono text-xs uppercase tracking-wide text-ink-muted">{meta}</p>
      ) : null}
    </div>
  );
}

/**
 * `SCA`, `SCA · 3 weeks to exam`, or `SCA · exam passed`.
 *
 * Whole weeks, and never a count of days: the old line rounded the same way,
 * and a countdown that ticks down by a day is a pressure nobody asked for.
 */
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
