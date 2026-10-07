"use client";

import { Button, type ButtonProps } from "@/foundation/ui";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";
import { useCanAuthor } from "@/capabilities/authoring/hooks/useCanAuthor";

/**
 * Primary actions use blue on staff console, B2B commit black elsewhere.
 * `write` hides the button from anyone who cannot author.
 */
export function AuthoringButton({
  variant,
  themeType,
  write = false,
  ...props
}: ButtonProps & { write?: boolean }) {
  const chrome = useAuthoringChrome();
  const canAuthor = useCanAuthor();
  if (write && !canAuthor) return null;
  const resolvedVariant =
    variant === "commit" ? chrome.primaryVariant : variant;
  return (
    <Button
      {...props}
      themeType={themeType ?? chrome.themeType}
      variant={resolvedVariant}
    />
  );
}
