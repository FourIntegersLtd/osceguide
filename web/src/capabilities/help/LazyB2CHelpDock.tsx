"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { AthenaFab } from "@/capabilities/help/AthenaFab";
import type { B2CHelpDockProps } from "@/capabilities/help/B2CHelpDock";
import { readAthenaLaunch, type AthenaLaunch } from "@/capabilities/help/api";

const B2CHelpDock = dynamic(
  () => import("@/capabilities/help/B2CHelpDock").then((mod) => ({ default: mod.B2CHelpDock })),
  { ssr: false },
);

/**
 * Defers loading LiveKit and the full dock until the user opens Athena.
 * The collapsed FAB is inline so staff/consumer shells stay light on navigation.
 */
export function LazyB2CHelpDock(props: B2CHelpDockProps) {
  const { isExpanded, setIsExpanded } = props;
  const [loadDock, setLoadDock] = useState(isExpanded);

  useEffect(() => {
    if (isExpanded) setLoadDock(true);
  }, [isExpanded]);

  // "Discuss with Athena" can fire before the dock has ever loaded, when nothing
  // else is listening. Catch it here, load the dock, and hand it the topic.
  const [pendingLaunch, setPendingLaunch] = useState<AthenaLaunch | null>(null);

  useEffect(() => {
    if (loadDock) return;
    const open = (event: Event) => {
      setPendingLaunch(readAthenaLaunch((event as CustomEvent<unknown>).detail));
      setLoadDock(true);
      setIsExpanded(true);
    };
    window.addEventListener("osce:open-athena", open);
    return () => window.removeEventListener("osce:open-athena", open);
  }, [loadDock, setIsExpanded]);

  const openHelp = useCallback(() => {
    setLoadDock(true);
    setIsExpanded(true);
  }, [setIsExpanded]);

  if (!loadDock) return <AthenaFab onClick={openHelp} />;

  return <B2CHelpDock {...props} initialLaunch={pendingLaunch} />;
}
