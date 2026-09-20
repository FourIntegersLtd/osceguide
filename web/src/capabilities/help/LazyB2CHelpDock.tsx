"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import { LuCircleHelp } from "react-icons/lu";
import { Button } from "@/foundation/ui";
import type { B2CHelpDockProps } from "@/capabilities/help/B2CHelpDock";

const B2CHelpDock = dynamic(
  () => import("@/capabilities/help/B2CHelpDock").then((mod) => ({ default: mod.B2CHelpDock })),
  { ssr: false },
);

/**
 * Defers loading LiveKit and the full help panel until the user opens help.
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

  if (!loadDock) {
    return (
      <div className="lg:h-full">
        <div className="fixed bottom-[calc(0.5rem+env(safe-area-inset-bottom,0px))] right-4 z-50">
          <Button
            type="button"
            variant="primary"
            size="lg"
            onClick={openHelp}
            className="h-11 w-11 px-0 lg:w-auto lg:gap-2 lg:px-4"
            aria-label="Need Help?"
          >
            <LuCircleHelp className="h-5 w-5 shrink-0" aria-hidden />
            <span className="hidden pr-0.5 font-medium lg:inline">Need Help?</span>
          </Button>
        </div>
      </div>
    );
  }

  return <B2CHelpDock {...props} />;
}
