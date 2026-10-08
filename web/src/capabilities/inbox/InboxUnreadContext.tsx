"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useMeEvents } from "@/foundation/hooks";
import type { InboxUnread } from "@/capabilities/inbox/useInboxUnread";

const NONE: InboxUnread = { count: 0, refresh: () => undefined, decrement: () => undefined, clear: () => undefined };

const InboxUnreadContext = createContext<InboxUnread>(NONE);

/** Its own component so an arm without an inbox never opens the event stream. */
function RefreshOnMessage({ onSignal }: { onSignal: () => void }) {
  useMeEvents(["message.received"], onSignal);
  return null;
}

export function InboxUnreadProvider({
  value,
  enabled,
  children,
}: {
  value: InboxUnread;
  enabled: boolean;
  children: ReactNode;
}) {
  return (
    <InboxUnreadContext.Provider value={value}>
      {enabled ? <RefreshOnMessage onSignal={value.refresh} /> : null}
      {children}
    </InboxUnreadContext.Provider>
  );
}

export function useInboxUnreadContext(): InboxUnread {
  return useContext(InboxUnreadContext);
}
