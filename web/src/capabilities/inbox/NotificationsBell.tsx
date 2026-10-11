"use client";

import Link from "next/link";
import { LuBell } from "react-icons/lu";
import { useSurface } from "@/capabilities/SurfaceContext";
import { inboxCapability } from "@/capabilities/inbox/capability";
import { useInboxUnreadContext } from "@/capabilities/inbox/InboxUnreadContext";
import { unreadLabel } from "@/capabilities/inbox/model";

/** The toolbar bell: a link to Notifications with the unread count. Nothing on a surface that has no inbox. */
export function NotificationsBell() {
  const { surface, hrefFor } = useSurface();
  const unread = useInboxUnreadContext();
  if (!inboxCapability.surfaces.includes(surface)) return null;
  return (
    <Link
      href={hrefFor(inboxCapability.path)}
      aria-label={unread.count > 0 ? `Notifications, ${unread.count} unread` : "Notifications"}
      className="relative inline-flex h-[30px] w-[30px] items-center justify-center rounded-osce-md text-b2c-text-secondary hover:bg-b2c-secondary"
    >
      <LuBell className="h-4 w-4" aria-hidden />
      {unread.count > 0 ? (
        <span className="absolute -right-1 -top-1 min-w-[1.1rem] rounded-full bg-osce-accent px-1 text-center text-osce-caption font-semibold leading-[1.1rem] text-white">
          {unreadLabel(unread.count)}
        </span>
      ) : null}
    </Link>
  );
}
