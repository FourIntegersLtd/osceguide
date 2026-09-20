"use client";

import Link from "next/link";
import { PiSparkle } from "react-icons/pi";
import { cn } from "@/foundation/ui";
import { b2cNavUpgradeButton } from "@/foundation/ui/productTokens";
import { useCurrentExam, useSession } from "@/foundation/session";
import { useSurface } from "@/capabilities";

/**
 * What sits under the consumer navigation: upgrade, who you are, what you sit.
 */
export function TrainNavFooter({ collapsed = false }: { collapsed?: boolean }) {
  const { session } = useSession();
  const { hrefFor } = useSurface();
  const { codes, code, setCode } = useCurrentExam();

  const displayName = session?.user.name || session?.user.email || "Account";
  const meta = examMeta(code, session?.user.exam_date ?? null);

  return (
    <div
      className={cn(
        "mt-auto shrink-0 border-t border-[#EDF1F5] py-5",
        collapsed ? "px-2 lg:px-2" : "px-4",
      )}
    >
      {codes.length === 0 && (
        <Link
          href={`${hrefFor("/settings")}?tab=payments`}
          className={cn(
            b2cNavUpgradeButton,
            "mb-4",
            collapsed ? "lg:h-11 lg:!px-0 lg:w-full" : "",
          )}
          title="Upgrade to Pro"
        >
          <PiSparkle className="h-4 w-4 shrink-0" aria-hidden />
          <span className={collapsed ? "lg:sr-only" : ""}>Upgrade to Pro</span>
        </Link>
      )}

      <div className={cn("text-center text-osce-meta text-b2c-text-secondary", collapsed && "lg:sr-only")}>
        <p className="truncate">{displayName}</p>

        {codes.length > 1 ? (
          <label className="mt-1 block">
            <span className="sr-only">Exam</span>
            <select
              value={code ?? ""}
              onChange={(event) => setCode(event.target.value)}
              className="w-full bg-transparent font-mono text-osce-micro font-medium uppercase tracking-[0.08em] leading-snug text-b2c-text-muted"
            >
              {codes.map((item) => (
                <option key={item} value={item}>
                  {item.toUpperCase()}
                </option>
              ))}
            </select>
          </label>
        ) : meta ? (
          <p className="mt-0.5 font-mono text-osce-micro font-medium uppercase tracking-[0.08em] leading-snug text-b2c-text-muted">
            {meta}
          </p>
        ) : null}
      </div>
    </div>
  );
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
