"use client";

import type { ReactNode } from "react";
import { HiOutlineExclamationTriangle } from "react-icons/hi2";
import { b2cCardPlain } from "@/foundation/ui/productTokens";
import { cn } from "@/foundation/ui/cn";
import { Button } from "@/foundation/ui/Button";
import { B2CSectionIconBadge } from "@/foundation/ui/B2CSectionIconBadge";

type B2CErrorStateProps = {
  title?: string;
  description?: string;
  onRetry?: () => void;
  retryLabel?: string;
  isRetrying?: boolean;
  secondaryAction?: ReactNode;
  className?: string;
  /** `card` renders a bordered panel; `plain` fits inside an existing card. */
  variant?: "card" | "plain";
};

/** Sibling of B2CEmptyState for failed loads. Never show "no data" for a failed request. */
export function B2CErrorState({
  title = "We couldn't load this",
  description = "Check your connection and try again.",
  onRetry,
  retryLabel = "Try again",
  isRetrying = false,
  secondaryAction,
  className = "",
  variant = "card",
}: B2CErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        variant === "card" ? b2cCardPlain : "",
        "flex flex-col items-center justify-center gap-3 px-6 py-12 text-center",
        className,
      )}
    >
      <B2CSectionIconBadge tone="rose" size="lg">
        <HiOutlineExclamationTriangle aria-hidden="true" />
      </B2CSectionIconBadge>
      <h3 className="text-osce-body font-semibold text-osce-ink-900">
        {title}
      </h3>
      {description ? (
        <p className="max-w-md text-osce-meta text-b2c-text-muted">
          {description}
        </p>
      ) : null}
      {onRetry || secondaryAction ? (
        <div className="mt-2 flex flex-wrap items-center justify-center gap-2">
          {onRetry ? (
            <Button
              type="button"
              variant="primary"
              size="sm"
              onClick={onRetry}
              isLoading={isRetrying}
            >
              {retryLabel}
            </Button>
          ) : null}
          {secondaryAction}
        </div>
      ) : null}
    </div>
  );
}

type B2CInlineErrorProps = {
  message: string | null | undefined;
  className?: string;
  id?: string;
};

/** Small inline error line for forms and cards. Renders nothing when empty. */
export function B2CInlineError({ message, className = "", id }: B2CInlineErrorProps) {
  if (!message) return null;
  return (
    <p
      id={id}
      role="alert"
      className={cn("text-osce-meta text-osce-danger", className)}
    >
      {message}
    </p>
  );
}