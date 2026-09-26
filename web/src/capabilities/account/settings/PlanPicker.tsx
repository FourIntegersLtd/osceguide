"use client";

import { useState } from "react";
import { HiOutlineArrowPath } from "react-icons/hi2";
import { PiSparkle } from "react-icons/pi";
import {
  ModalContent,
  ModalHelper,
  ModalPrimaryButton,
  cn,
  productTokens,
} from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { hasCode } from "@/foundation/platform-client";
import { startCheckout, type Plan } from "@/capabilities/account/api";

const { b2cFieldLabel, b2cLink, b2cSettingsFieldInput } = productTokens;

/**
 * Pick a plan, and pay for it.
 *
 * This is the only way anybody buys anything, so what it does and does not do
 * both matter. It sends a **plan code** — never a price — and then hands the
 * browser to Stripe's hosted page; no card detail passes through here, and
 * nothing in this file can grant access. The plans, their prices and their
 * durations are the backend's answer to `/billing/plans` rather than four
 * constants compiled into the bundle, which is how the retiring client came to
 * show one price and charge another after a change in Stripe.
 *
 * A friend's referral code is optional. Typing one shows each plan's 10%-off
 * price, but only the backend decides whether the code is good: it refuses an
 * unknown code (or the buyer's own) before Stripe is ever opened.
 */
export default function PlanPicker({
  plans,
  variant = "page",
}: {
  plans: Plan[];
  variant?: "modal" | "page";
}) {
  const [selected, setSelected] = useState<string | null>(plans[0]?.code ?? null);
  const [agreedToPolicies, setAgreedToPolicies] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [referralCode, setReferralCode] = useState("");

  const chosen = plans.find((plan) => plan.code === selected) ?? null;
  // Blank means "no code": the full price, and nothing sent to the backend.
  const trimmedReferralCode = referralCode.trim();
  const hasReferralCode = trimmedReferralCode.length > 0;

  const handleCheckout = async () => {
    setError(null);
    if (!agreedToPolicies) {
      setError(
        "You must agree to the Terms of Service including our No Refund Policy before proceeding.",
      );
      return;
    }
    if (!chosen) return;

    setIsLoading(true);
    try {
      const { checkout_url } = await startCheckout(
        chosen.code,
        hasReferralCode ? trimmedReferralCode : null,
      );
      // Leave `isLoading` true: the browser is on its way to Stripe, and a
      // button that springs back to "Upgrade" invites a second checkout.
      window.location.assign(checkout_url);
    } catch (cause) {
      // A refused code is the buyer's to fix, so say so plainly. Everything
      // else is ours, and they need to hear no money moved.
      if (hasCode(cause, "referral_not_found")) {
        setError("That referral code is not valid. Check it, or clear it to pay the full price.");
      } else if (hasCode(cause, "referral_discount_unavailable")) {
        setError("That plan has no referral discount. Choose another plan, or clear the code.");
      } else {
        setError(
          `${errorMessage(cause)} No money has left your account. Please try again or email ${SUPPORT_EMAIL}.`,
        );
      }
      setIsLoading(false);
    }
  };

  const planListBleed = variant === "page" ? "-mx-3 sm:-mx-4" : "-mx-4 lg:-mx-6";
  const planRowPadding = variant === "page" ? "px-3 sm:px-4" : "px-4 lg:px-6";

  return (
    <ModalContent className="w-full">
      <ModalHelper className="mb-5 mt-0">
        Choose the option that suits you best
      </ModalHelper>

      <div className={cn("divide-y divide-b2c-border", planListBleed)}>
        {plans.map((plan) => {
          const isSelected = selected === plan.code;
          return (
            <button
              key={plan.code}
              type="button"
              onClick={() => setSelected(plan.code)}
              aria-pressed={isSelected}
              className={cn(
                "flex w-full flex-col items-start gap-1 py-4 text-left transition sm:flex-row sm:items-center sm:justify-between sm:gap-4",
                planRowPadding,
                isSelected
                  ? "bg-osce-accent-muted hover:bg-osce-accent-subtle"
                  : "hover:bg-b2c-surface-muted",
              )}
            >
              <span className="min-w-0">
                <span
                  className={cn(
                    "block text-osce-body font-medium",
                    isSelected ? "text-osce-accent-hover" : "text-osce-ink-900",
                  )}
                >
                  {planTitle(plan)}
                </span>
                <span className="mt-0.5 block text-osce-meta leading-relaxed text-b2c-text-muted">
                  {planDescription(plan)}
                </span>
              </span>
              <span
                className={cn(
                  "flex shrink-0 items-center gap-2 text-osce-body font-semibold sm:whitespace-nowrap",
                  isSelected ? "text-osce-accent-hover" : "text-osce-accent",
                )}
              >
                <PlanPrice plan={plan} hasReferralCode={hasReferralCode} />
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-6">
        <label htmlFor="checkout-referral-code" className={b2cFieldLabel}>
          Friend&apos;s referral code (optional)
        </label>
        <input
          id="checkout-referral-code"
          className={`mt-1.5 ${b2cSettingsFieldInput}`}
          value={referralCode}
          onChange={(event) => setReferralCode(event.target.value)}
          placeholder="Enter a code for 10% off"
          autoComplete="off"
          maxLength={32}
        />
      </div>

      <div className="mt-6 flex items-start gap-3">
        <input
          id="policies"
          type="checkbox"
          checked={agreedToPolicies}
          onChange={() => setAgreedToPolicies(!agreedToPolicies)}
          className="mt-1 h-4 w-4 shrink-0 rounded border-b2c-border text-osce-accent focus:ring-osce-accent/20"
        />
        <label htmlFor="policies" className="text-osce-meta text-b2c-text-muted">
          I agree to the{" "}
          <a href="/compliances/terms-of-service" className={b2cLink}>
            Terms of Service
          </a>{" "}
          (including our No Refund Policy)
        </label>
      </div>

      <div className="mt-6 space-y-3">
        <div className="flex sm:justify-end">
          <ModalPrimaryButton
            onClick={handleCheckout}
            disabled={isLoading || !chosen}
            className="inline-flex w-full items-center justify-center gap-2 whitespace-nowrap sm:w-auto"
          >
            {isLoading ? (
              <>
                <HiOutlineArrowPath className="h-4 w-4 shrink-0 animate-spin" aria-hidden />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <PiSparkle className="h-4 w-4 shrink-0" aria-hidden />
                <span>
                  Upgrade Now
                  {chosen
                    ? ` · ${formatMoney(chargedPence(chosen, hasReferralCode), chosen.currency)}`
                    : ""}
                </span>
              </>
            )}
          </ModalPrimaryButton>
        </div>
        {error ? (
          <p className="text-osce-meta text-osce-danger sm:text-right">{error}</p>
        ) : null}
        <ModalHelper className="mt-0 sm:text-right">
          Secure payment powered by Stripe
        </ModalHelper>
      </div>
    </ModalContent>
  );
}

/**
 * A plan's price: the full price alone, or struck through beside the 10%-off
 * price once a referral code is typed and the plan has a discounted price.
 */
function PlanPrice({ plan, hasReferralCode }: { plan: Plan; hasReferralCode: boolean }) {
  const discountedPence = hasReferralCode ? plan.referral_amount_pence : null;
  if (discountedPence == null) return <>{formatMoney(plan.amount_pence, plan.currency)}</>;
  return (
    <>
      <s className="font-normal text-b2c-text-muted">{formatMoney(plan.amount_pence, plan.currency)}</s>
      {formatMoney(discountedPence, plan.currency)}
    </>
  );
}

/** What the buyer will be charged: the referral price when a code is typed and the plan has one. */
function chargedPence(plan: Plan, hasReferralCode: boolean): number {
  return (hasReferralCode ? plan.referral_amount_pence : null) ?? plan.amount_pence;
}

export const SUPPORT_EMAIL = "hello@fourintegers.com";

/** Months, because a plan is sold in months and stored in days. */
export function planTitle(plan: Plan): string {
  const months = Math.round(plan.duration_days / 30);
  const period = months >= 1 ? `${months}-Month` : `${plan.duration_days}-Day`;
  return plan.exam_code ? `${plan.exam_code.toUpperCase()} · ${period} Access` : `${period} Access`;
}

export function planDescription(plan: Plan): string {
  return plan.exam_code
    ? `${plan.duration_days} days of ${plan.exam_code.toUpperCase()} practice`
    : `${plan.duration_days} days of practice across every exam`;
}

export function formatMoney(pence: number, currency: string): string {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: currency.toUpperCase(),
  }).format(pence / 100);
}
