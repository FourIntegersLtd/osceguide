"use client";

import { HiOutlineInformationCircle } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { B2CHero } from "@/foundation/ui/B2CHero";

/** What the marketplace is, said once at the top; the exam is named by the backend. */
export function MarketplaceIntroCard({
  examName,
  onLearnMore,
}: {
  examName: string | null;
  onLearnMore: () => void;
}) {
  const examLabel = examName ?? "same";
  return (
    <B2CHero
      eyebrow="Colleague video sessions"
      title={`Practise the ${examLabel} exam with a colleague over video`}
      action={
        <Button type="button" variant="secondary" onClick={onLearnMore} className="gap-1.5">
          <HiOutlineInformationCircle className="h-4 w-4" aria-hidden />
          Learn how it works
        </Button>
      }
    >
      Post your availability or claim someone&apos;s slot. Roles are assigned automatically, and the
      timers start when you both join.
    </B2CHero>
  );
}
