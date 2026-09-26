"use client";

import Link from "next/link";
import { PERSONAL_WORKSPACE, workspaceBasePath } from "@/foundation/routing";
import { useSession } from "@/foundation/session";

/** Staff rail footer — name, and the way back to their own practice. */
export function StaffNavFooter({ collapsed = false }: { collapsed?: boolean }) {
  const { session } = useSession();
  const displayName = session?.user.name || session?.user.email || "Staff";

  if (collapsed) return null;

  return (
    <div className="mt-auto shrink-0 border-t border-[#EDF1F5] px-4 py-5 text-center text-osce-meta text-b2c-text-secondary">
      <p className="truncate">{displayName}</p>
      <Link href={workspaceBasePath(PERSONAL_WORKSPACE)} className="mt-1 block font-medium text-osce-accent hover:underline">
        My practice
      </Link>
    </div>
  );
}
