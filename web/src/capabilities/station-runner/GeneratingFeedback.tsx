"use client";

import { ModalContent, ModalHelper, ModalTitle, Spinner } from "@/foundation/ui";

/** Non-SCA marking wait animation — matches legacy `GeneratingFeedback`. */
export function GeneratingFeedback() {
  return (
    <ModalContent className="flex flex-col items-center space-y-3 text-center">
      <Spinner size="md" label="Generating" />
      <ModalTitle className="text-osce-body">Generating your feedback</ModalTitle>
      <div className="space-y-1">
        <ModalHelper>
          We are reviewing your performance and preparing detailed feedback.
        </ModalHelper>
        <p className="text-osce-body text-b2c-text-muted">
          This usually takes one to three minutes. You can start another station in the meantime;
          we&apos;ll let you know when it&apos;s ready.
        </p>
      </div>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-b2c-surface-muted"
        role="progressbar"
        aria-label="Marking in progress"
      >
        <div className="h-full w-1/3 animate-pulse rounded-full bg-osce-accent" />
      </div>
    </ModalContent>
  );
}
