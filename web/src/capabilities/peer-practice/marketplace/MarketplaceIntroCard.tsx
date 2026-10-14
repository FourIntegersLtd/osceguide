"use client";

import { HiOutlineInformationCircle } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { B2CHero } from "@/foundation/ui/B2CHero";
import { INTRO_DESCRIPTION, introTitle } from "@/capabilities/peer-practice/marketplace/copy";

/** What the marketplace is, said once at the top; the exam is named by the backend. */
export function MarketplaceIntroCard({
  examName,
  onLearnMore,
}: {
  examName: string | null;
  onLearnMore: () => void;
}) {
  return (
    <B2CHero
      title={introTitle(examName)}
      action={
        <Button type="button" variant="secondary" onClick={onLearnMore} className="gap-1.5">
          <HiOutlineInformationCircle className="h-4 w-4" aria-hidden />
          Learn how it works
        </Button>
      }
    >
      {INTRO_DESCRIPTION}
    </B2CHero>
  );
}
