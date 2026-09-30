"use client";

import dynamic from "next/dynamic";
import { useCallback, useState } from "react";
import { LuCircleHelp } from "react-icons/lu";
import { Button } from "@/foundation/ui";
import type { HelpNavItem } from "@/capabilities/help/HelpPanel";

const HelpPanel = dynamic(
  () => import("@/capabilities/help/HelpPanel").then((mod) => ({ default: mod.HelpPanel })),
  { ssr: false },
);

/**
 * Defers LiveKit and the full help dialog until the user opens help.
 * Institution/assess shells use this instead of a static `HelpPanel` import.
 */
export function LazyHelpPanel({ navItems = [] }: { navItems?: HelpNavItem[] }) {
  const [loadPanel, setLoadPanel] = useState(false);

  const openHelp = useCallback(() => {
    setLoadPanel(true);
  }, []);

  if (!loadPanel) {
    return (
      <Button
        variant="secondary"
        size="sm"
        onClick={openHelp}
        className="fixed bottom-5 right-5 z-40 shadow-lg"
        aria-haspopup="dialog"
      >
        <LuCircleHelp className="h-4 w-4" aria-hidden /> Help
      </Button>
    );
  }

  return <HelpPanel navItems={navItems} initialOpen={true} />;
}
