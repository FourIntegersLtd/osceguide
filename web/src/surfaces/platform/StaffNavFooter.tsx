"use client";

import { useSession } from "@/foundation/session";

/** Staff rail footer — name only (no exam switcher). */
export function StaffNavFooter({ collapsed = false }: { collapsed?: boolean }) {
  const { session } = useSession();
  const displayName = session?.user.name || session?.user.email || "Staff";

  if (collapsed) return null;

  return (
    <div className="mt-auto shrink-0 border-t border-[#EDF1F5] px-4 py-5 text-center text-osce-meta text-b2c-text-secondary">
      <p className="truncate">{displayName}</p>
    </div>
  );
}
