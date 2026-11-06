"use client";

import type { ReactNode } from "react";
import { boardBtn } from "@/foundation/ui/boardKit";
import { Spinner } from "@/foundation/ui/Spinner";
import { useHydrated } from "@/foundation/hooks";

/**
 * The full-width pill button of every sign-in, sign-up and password screen.
 *
 * A submit is inert until hydrated: before React owns the form a native submit
 * would put the password in the URL as a GET query.
 */
export default function AuthButton({
  isLoading = false,
  disabled = false,
  type = "submit",
  variant = "brand",
  onClick,
  children,
}: {
  isLoading?: boolean;
  disabled?: boolean;
  type?: "submit" | "button";
  variant?: "brand" | "line";
  onClick?: () => void;
  children: ReactNode;
}) {
  const hydrated = useHydrated();
  return (
    <button
      type={type}
      className={`${boardBtn(variant === "brand" ? "primary" : "default")} w-full`}
      aria-busy={isLoading || undefined}
      disabled={(type === "submit" && !hydrated) || disabled || isLoading}
      onClick={onClick}
    >
      {isLoading ? <Spinner size="sm" className="text-current" /> : null}
      {children}
    </button>
  );
}
