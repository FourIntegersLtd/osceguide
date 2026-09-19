"use client";

import type { ReactNode } from "react";
import { ToastProvider } from "@/foundation/ui/toast";
import { B2CToastViewport } from "@/foundation/ui/B2CToastViewport";

export function B2CToastProvider({ children }: { children: ReactNode }) {
  return (
    <ToastProvider
      renderViewport={(toasts, dismiss) => (
        <B2CToastViewport toasts={toasts} onDismiss={dismiss} />
      )}
    >
      {children}
    </ToastProvider>
  );
}
