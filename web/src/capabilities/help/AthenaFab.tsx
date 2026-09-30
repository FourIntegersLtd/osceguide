"use client";

import Image from "next/image";
import { ATHENA_IMAGE_SRC, Button } from "@/foundation/ui";

/**
 * The button that opens Athena, bottom right of every signed-in screen.
 *
 * Her face rather than a help icon: she is the tutor who knows this person,
 * and a question mark reads as a manual. Shared by the lazy placeholder and
 * the loaded dock so the button does not change when the dock loads.
 */
export function AthenaFab({ onClick }: { onClick: () => void }) {
  return (
    <div className="lg:h-full">
      <div className="fixed bottom-[calc(0.5rem+env(safe-area-inset-bottom,0px))] right-4 z-50">
        <Button
          type="button"
          variant="primary"
          size="lg"
          onClick={onClick}
          className="h-11 w-11 px-0 lg:w-auto lg:gap-2 lg:pl-1.5 lg:pr-4"
          aria-label="Talk to Athena"
        >
          <Image
            src={ATHENA_IMAGE_SRC}
            alt=""
            width={32}
            height={32}
            className="h-8 w-8 shrink-0 rounded-full border border-white/40 object-cover object-top"
          />
          <span className="hidden font-medium lg:inline">Athena</span>
        </Button>
      </div>
    </div>
  );
}
