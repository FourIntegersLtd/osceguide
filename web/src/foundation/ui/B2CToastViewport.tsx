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
    <div className="pointer-events-none fixed inset-x-4 bottom-4 z-[110] flex flex-col gap-2 sm:inset-x-auto sm:bottom-6 sm:right-6 sm:w-[22rem]">
      {toasts.map((toast) => (
        <B2CToastCard key={toast.id} toast={toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
