"use client";

import type { ReactNode } from "react";
import { Button } from "@/foundation/ui";
import { useHydrated } from "@/foundation/hooks";
import { authButtonPrimary } from "@/foundation/ui/authTheme";

/**
 * The submit of every sign-in, sign-up and password form.
 *
 * Inert until hydrated: before React owns the form a native submit would put
 * the password in the URL as a GET query.
 */
export default function AuthSubmitButton({
  isLoading,
  disabled = false,
  children,
}: {
  isLoading: boolean;
  disabled?: boolean;
  children: ReactNode;
}) {
  const hydrated = useHydrated();
  return (
    <Button
      type="submit"
      variant="commit"
      themeType="b2c"
      fullWidth
      size="lg"
      isLoading={isLoading}
      disabled={!hydrated || disabled}
      className={authButtonPrimary}
    >
      {children}
    </Button>
  );
}
