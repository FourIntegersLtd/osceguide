"use client";

import { cn } from "@/foundation/ui";
import { useSession } from "@/foundation/session";

/** Staff rail footer — name only (no exam switcher). */
export function StaffNavFooter({ collapsed = false }: { collapsed?: boolean }) {
  const { session } = useSession();
  const displayName = session?.user.name || session?.user.email || "Staff";

  return (
    <div
      className={cn(
        "mt-auto shrink-0 border-t border-[#EDF1F5] py-5 text-center text-osce-meta text-b2c-text-secondary",
        collapsed ? "px-2 lg:px-2" : "px-4",
      )}
    >
      <p className={cn("truncate", collapsed && "lg:sr-only")}>{displayName}</p>
    </div>
  );
}
