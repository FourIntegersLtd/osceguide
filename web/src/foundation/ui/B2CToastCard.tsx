"use client";

import {
  HiOutlineCheckCircle,
  HiOutlineExclamationCircle,
  HiOutlineExclamationTriangle,
  HiOutlineInformationCircle,
  HiOutlineXMark,
} from "react-icons/hi2";
import type { CSSProperties } from "react";
import Link from "next/link";
import { b2cButtonPrimary } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import type { ToastItem, ToastTone } from "@/foundation/ui/toast";

const toneStyles: Record<
  ToastTone,
  {
    well: string;
    track: string;
    bar: string;
    Icon: typeof HiOutlineCheckCircle;
  }
> = {
  success: {
    well: "bg-osce-success-bg text-osce-success-text",
    track: "bg-osce-success-bg",
    bar: "bg-osce-success-icon",
    Icon: HiOutlineCheckCircle,
  },
  error: {
    well: "bg-osce-danger-bg text-osce-danger",
    track: "bg-osce-danger-bg",
    bar: "bg-osce-danger-icon",
    Icon: HiOutlineExclamationCircle,
  },
  warning: {
    well: "bg-osce-warning-bg text-osce-warning-text",
    track: "bg-osce-warning-bg",
    bar: "bg-osce-warning-icon",
    Icon: HiOutlineExclamationTriangle,
  },
  info: {
    well: "bg-osce-accent-muted text-osce-accent-hover",
    track: "bg-osce-accent-muted",
    bar: "bg-osce-accent",
    Icon: HiOutlineInformationCircle,
  },
};

interface B2CToastCardProps {
  toast: ToastItem;
  onDismiss: (id: string) => void;
}

export function B2CToastCard({ toast, onDismiss }: B2CToastCardProps) {
  const { well, track, bar, Icon } = toneStyles[toast.tone];
  const isError = toast.tone === "error";
  const action = toast.action;

  const handleAction = () => {
    action?.onClick?.();
    onDismiss(toast.id);
  };

  return (
    <div
      role={isError ? "alert" : "status"}
      aria-live={isError ? "assertive" : "polite"}
      className="pointer-events-auto overflow-hidden rounded-osce-lg border border-b2c-border bg-osce-surface shadow-[0_8px_24px_rgba(16,24,40,0.12)]"
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          <span
            className={cn(
              "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
              well,
            )}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-osce-body font-semibold text-osce-ink-900">
              {toast.title}
            </p>
            {toast.message ? (
              <p className="mt-0.5 text-osce-meta text-b2c-text-muted">
                {toast.message}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={() => onDismiss(toast.id)}
            aria-label="Dismiss notification"
            className="shrink-0 text-b2c-text-muted transition-colors hover:text-osce-ink-900"
          >
            <HiOutlineXMark className="h-3.5 w-3.5" aria-hidden />
          </button>
        </div>
        {action ? (
          <div className="mt-3 flex justify-end">
            {action.href ? (
              <Link
                href={action.href}
                onClick={handleAction}
                className={cn(
                  b2cButtonPrimary,
                  "w-full justify-center sm:w-auto",
                )}
              >
                {action.label}
              </Link>
            ) : (
              <button
                type="button"
                onClick={handleAction}
                className={cn(
                  b2cButtonPrimary,
                  "w-full justify-center sm:w-auto",
                )}
              >
                {action.label}
              </button>
            )}
          </div>
        ) : null}
      </div>
      {/* Countdown to auto-dismiss. Persistent toasts show no track at all. */}
      {toast.resolvedDurationMs !== null ? (
        <div className={cn("h-1 w-full", track)} aria-hidden>
          <div
            key={toast.createdAt}
            className={cn("osce-toast-progress-bar h-full w-full", bar)}
            style={
              {
                ["--toast-duration" as string]: `${toast.resolvedDurationMs}ms`,
              } as CSSProperties
            }
          />
        </div>
      ) : null}
    </div>
  );
}
