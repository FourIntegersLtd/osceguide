"use client";

import type { ReactNode } from "react";
import Image from "next/image";
import { cn } from "@/foundation/ui/cn";
import {
  b2cBodyTextMuted,
  b2cGroupedRowTitle,
} from "@/foundation/ui/productTokens";

/** Help-section Athena asset. single source of truth. */
export const ATHENA_IMAGE_SRC = "/images/athena.png";

/** Default helper copy from the Help home screen. */
export const ATHENA_DEFAULT_DESCRIPTION =
  "Browse guides, get voice help navigating the app, or ask clinical questions.";

export type AthenaIdentityLayout = "stack" | "inline";

export type AthenaIdentityProps = {
  /** Defaults to "Athena" (Help baseline). */
  title?: string;
  /** Defaults to the Help home description. Pass `null` To hide. */
  description?: ReactNode | null;
  /** `stack` = centered Help hero; `inline` = compact row for toolbars/cards. */
  layout?: AthenaIdentityLayout;
  className?: string;
  /** Optional class on the avatar image only. */
  imageClassName?: string;
  alt?: string;
};

/**
 * Unified Athena identity. avatar + name + helper copy.
 * Use everywhere Athena is shown instead of ad-hoc `/images/athena.png` Markup.
 */
export function AthenaIdentity({
  title = "Athena",
  description = ATHENA_DEFAULT_DESCRIPTION,
  layout = "stack",
  className = "",
  imageClassName = "",
  alt = "Athena",
}: AthenaIdentityProps) {
  const avatar = (
    <Image
      src={ATHENA_IMAGE_SRC}
      alt={alt}
      width={48}
      height={48}
      className={cn(
        "h-12 w-12 shrink-0 rounded-full border-2 border-osce-accent-subtle object-cover object-top shadow-md",
        layout === "stack" && "mb-2",
        imageClassName,
      )}
    />
  );

  if (layout === "inline") {
    return (
      <div
        className={cn(
          "flex min-w-0 items-center gap-3 text-left",
          className,
        )}
      >
        {avatar}
        <div className="min-w-0">
          <p className={cn(b2cGroupedRowTitle, "truncate font-semibold leading-tight")}>
            {title}
          </p>
          {description != null ? (
            <p className={cn(b2cBodyTextMuted, "mt-0.5 truncate leading-tight")}>
              {description}
            </p>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex flex-col items-center text-center",
        className,
      )}
    >
      {avatar}
      <h3 className={cn(b2cGroupedRowTitle, "font-semibold")}>{title}</h3>
      {description != null ? (
        <p className={cn(b2cBodyTextMuted, "mt-1 max-w-[18rem]")}>
          {description}
        </p>
      ) : null}
    </div>
  );
}

export default AthenaIdentity;
