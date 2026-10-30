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

/**
 * Athena's round avatar, the one place her picture is cropped. The portrait
 * is taller than a circle, so a plain `object-cover` cut her hair off; here
 * the picture is set a little smaller with headroom, on its own white
 * background. Size and border come from `className` (for example `h-11 w-11`).
 */
export function AthenaAvatar({ className = "", alt = "" }: { className?: string; alt?: string }) {
  return (
    <span aria-hidden={alt ? undefined : true} className={cn("relative block shrink-0 overflow-hidden rounded-full bg-white", className)}>
      <Image
        src={ATHENA_IMAGE_SRC}
        alt={alt}
        width={72}
        height={103}
        sizes="72px"
        className="absolute left-[3%] top-[7%] h-auto w-[94%] max-w-none"
      />
    </span>
  );
}

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
    <AthenaAvatar
      alt={alt}
      className={cn(
        "h-12 w-12 border-2 border-osce-accent-subtle shadow-md",
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
          <p className={cn(b2cGroupedRowTitle, "truncate font-heading font-semibold leading-tight")}>
            {title}
          </p>
          {description != null ? (
            <p className={cn(b2cBodyTextMuted, "mt-0.5 line-clamp-2 leading-snug")}>
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
