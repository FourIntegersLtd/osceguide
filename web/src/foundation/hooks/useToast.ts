"use client";

import { useToastContext } from "@/foundation/ui/toast";

/** B2C toast API: `toast.success(title, message)`, `toast.show({...})`. */
export function useToast() {
  return useToastContext();
}
