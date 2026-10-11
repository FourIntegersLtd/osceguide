"use client";

import { LuCircleHelp } from "react-icons/lu";
import { Button } from "@/foundation/ui";

/**
 * The Help button on phones, bottom right of every signed-in screen. From md
 * up the workspace toolbar carries the same button.
 *
 * A neutral help icon, not her face: Help is text-only on some routes, so the
 * button cannot promise a voice. Shared by the lazy placeholder and the loaded
 * dock so the button does not change when the dock loads.
 */
export function AthenaFab({ onClick }: { onClick: () => void }) {
  return (
    <div className="md:hidden">
      <div className="fixed bottom-[calc(0.5rem+env(safe-area-inset-bottom,0px))] right-4 z-50">
        <Button
          type="button"
          variant="primary"
          size="lg"
          onClick={onClick}
          className="h-11 gap-2 px-4"
        >
          <LuCircleHelp className="h-5 w-5 shrink-0" aria-hidden />
          <span className="font-medium">Help</span>
        </Button>
      </div>
    </div>
  );
}
