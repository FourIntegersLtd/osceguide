"use client";

import { useEffect } from "react";
import Link from "next/link";
import Modal from "@/foundation/ui/Modal";
import {
  ModalContent,
  ModalHelper,
  ModalPrimaryButton,
  ModalSecondaryButton,
  ModalTitle,
} from "@/foundation/ui/ModalContent";

export default function CookiesConsentModal({
  setAnalyticsEnabled,
}: {
  setAnalyticsEnabled: (enabled: boolean) => void;
}) {
  useEffect(() => {
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, []);

  const handleAccept = () => {
    localStorage.setItem("analytics-consent", "accepted");
    setAnalyticsEnabled(true);
  };

  const handleReject = () => {
    localStorage.setItem("analytics-consent", "rejected");
    setAnalyticsEnabled(false);
  };

  return (
    <Modal width="min(95vw, 560px)" height="fit-content">
      <ModalContent className="mx-auto max-w-md space-y-4 px-1 py-1 text-center">
        <p className="text-osce-meta font-medium uppercase tracking-[0.18em] text-osce-ink-500">
          OSCE Guide
        </p>
        <div>
          <ModalTitle className="text-osce-body">
            Your privacy comes first
          </ModalTitle>
          <ModalHelper className="mx-auto mt-1.5 max-w-[40ch]">
            We use essential cookies to keep you signed in and secure. Analytics
            cookies are optional. they help us improve the product, and you can
            turn them off anytime.
          </ModalHelper>
        </div>
        <div className="flex w-full flex-col gap-2">
          <ModalPrimaryButton className="w-full" onClick={handleAccept}>
            Allow analytics
          </ModalPrimaryButton>
          <ModalSecondaryButton className="w-full" onClick={handleReject}>
            Continue without analytics
          </ModalSecondaryButton>
        </div>
        <Link
          href="/compliances/cookies-policy"
          className="inline-block text-osce-meta text-osce-ink-500 underline decoration-osce-border underline-offset-[3px] transition-colors hover:text-osce-ink-900"
        >
          Cookie Policy
        </Link>
      </ModalContent>
    </Modal>
  );
}
