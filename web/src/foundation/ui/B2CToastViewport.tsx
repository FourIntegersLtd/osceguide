"use client";

import type { ToastItem } from "@/foundation/ui/toast";
import { B2CToastCard } from "@/foundation/ui/B2CToastCard";

interface B2CToastViewportProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

/** z-[110] sits above Modal (z-[100]) so "saved" toasts show over dialogs. */
export function B2CToastViewport({ toasts, onDismiss }: B2CToastViewportProps) {
  if (toasts.length === 0) return null;
  return (
    <div className="pointer-events-none fixed top-4 left-1/2 z-[110] flex w-[calc(100%-2rem)] -translate-x-1/2 flex-col gap-2 sm:w-[24rem]">
      {toasts.map((toast) => (
        <B2CToastCard key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
