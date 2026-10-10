"use client";

import Image from "next/image";
import { ATHENA_IMAGE_SRC, Button } from "@/foundation/ui";

/**
 * The Help button on phones, bottom right of every signed-in screen. From md
 * up the workspace toolbar carries the same button.
 *
 * Her face rather than a help icon: she is the tutor who knows this person,
 * and a question mark reads as a manual. Shared by the lazy placeholder and
 * the loaded dock so the button does not change when the dock loads.
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
          className="h-11 gap-2 pl-1.5 pr-4"
        >
          <Image
            src={ATHENA_IMAGE_SRC}
            alt=""
            width={32}
            height={32}
            className="h-8 w-8 shrink-0 rounded-full border border-white/40 object-cover object-top"
          />
          <span className="font-medium">Help</span>
        </Button>
      </div>
    </div>
  );
}
