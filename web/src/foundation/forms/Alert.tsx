"use client";

import { useEffect, useRef } from "react";
import { useOptionalToastContext } from "@/foundation/ui/toast";

interface LinkProps {
  href: string;
  text: string;
  subtext?: string;
}

interface AlertProps {
  message: string;
  type: "success" | "error";
  className?: string;
  link?: LinkProps;
  appearance?: "default" | "band";
}

const SHORT_TITLE_LIMIT = 64;

/**
 * Transient feedback bridge: every `<Alert message type />` now surfaces as a
 * toast (global, dismissible, announced to screen readers) and renders nothing
 * inline. Field-level validation should use AuthFormField `error` instead;
 * load failures should use B2CErrorState.
 */
function Alert({ message, type, link }: AlertProps) {
  const toast = useOptionalToastContext();
  const idRef = useRef<string | null>(null);

  useEffect(() => {
    if (!toast || !message) return;
    const trimmed = message.trim();
    const short = trimmed.length <= SHORT_TITLE_LIMIT;
    const title = short
      ? trimmed
      : type === "success"
        ? "Done"
        : "Something went wrong";
    idRef.current = toast.show({
      id: idRef.current ?? undefined,
      tone: type,
      title,
      message: short ? undefined : trimmed,
      action: link ? { label: link.text, href: link.href } : undefined,
    });
    // Only re-toast when the content changes; `toast` is a stable context.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message, type, link?.href, link?.text]);

  return null;
}

export default Alert;
