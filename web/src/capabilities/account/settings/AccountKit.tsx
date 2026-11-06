"use client";

import type { ComponentType, ReactNode } from "react";
import { Button, Panel } from "@/foundation/ui";
import { boardBtn, boardPadWide } from "@/foundation/ui/boardKit";
import { cn } from "@/foundation/ui/cn";
import { isOrgSurface } from "@/capabilities/surface";
import { useSurface } from "@/capabilities/SurfaceContext";

/**
 * The shared account screen wears two skins. An organisation's surfaces draw it as the Settings board's
 * cards and buttons (`boardKit`); the trainee's surface keeps the `Panel` and `Button` it always had.
 * Behaviour is identical in both: only the class strings and the icons differ.
 */
export function useBoardSkin(): boolean {
  return isOrgSurface(useSurface().surface);
}

/** One card: the board's `.card.pad` with an h2 and a `.meta` line, or the trainee `Panel`. */
export function AccountCard({
  title,
  description,
  tone,
  children,
}: {
  title: string;
  description?: string;
  /** `danger` colours the title (Delete your account). */
  tone?: "danger";
  children?: ReactNode;
}) {
  if (!useBoardSkin()) {
    return (
      <Panel title={title} description={description}>
        {children}
      </Panel>
    );
  }
  return (
    <section className={boardPadWide}>
      <h2 className={cn("m-0 text-assess-state-title font-semibold", tone === "danger" ? "text-osce-danger-text" : "text-ink")}>{title}</h2>
      {description ? <p className="m-0 text-assess-meta leading-normal text-ink-muted">{description}</p> : null}
      {children}
    </section>
  );
}

type AccountButtonProps = {
  variant?: "primary" | "secondary" | "danger";
  /** The board's `.btn.sm`. */
  small?: boolean;
  /** Drawn on the trainee surface only; the board's buttons carry no icon. */
  icon?: ComponentType<{ className?: string }>;
  type?: "button" | "submit";
  onClick?: () => void;
  disabled?: boolean;
  isLoading?: boolean;
  className?: string;
  children: ReactNode;
};

export function AccountButton({ variant = "primary", small, icon: Icon, type = "button", onClick, disabled, isLoading, className, children }: AccountButtonProps) {
  if (!useBoardSkin()) {
    return (
      <Button type={type} variant={variant} onClick={onClick} disabled={disabled} isLoading={isLoading} className={cn(Icon ? "gap-2" : undefined, className)}>
        {Icon ? <Icon className="h-4 w-4" aria-hidden /> : null}
        {children}
      </Button>
    );
  }
  const kind = variant === "secondary" ? "default" : variant;
  return (
    <button type={type} onClick={onClick} disabled={disabled || isLoading} aria-busy={isLoading || undefined} className={cn(boardBtn(kind, small), className)}>
      {children}
    </button>
  );
}
