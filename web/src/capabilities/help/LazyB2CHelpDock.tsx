"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { AthenaFab } from "@/capabilities/help/AthenaFab";
import type { B2CHelpDockProps } from "@/capabilities/help/B2CHelpDock";

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

  const openHelp = useCallback(() => {
    setLoadDock(true);
    setIsExpanded(true);
  }, [setIsExpanded]);

  if (!loadDock) return <AthenaFab onClick={openHelp} />;

  return <B2CHelpDock {...props} />;
}
