"use client";

import { Button, type ButtonProps } from "@/foundation/ui";
import { useAuthoringChrome } from "@/capabilities/authoring/parts/useAuthoringChrome";

/** Primary actions use blue on staff console, B2B commit black elsewhere. */
export function AuthoringButton({ variant, themeType, ...props }: ButtonProps) {
  const chrome = useAuthoringChrome();
  const resolvedVariant = variant === "commit" ? chrome.primaryVariant : variant;
  return (
    <Button {...props} themeType={themeType ?? chrome.themeType} variant={resolvedVariant} />
  );
}
