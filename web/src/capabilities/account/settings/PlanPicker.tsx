"use client";

import { useState } from "react";
import { HiOutlineArrowPath } from "react-icons/hi2";
import { PiSparkle } from "react-icons/pi";
import { Button, Checkbox, Input, ModalContent, ModalHelper, cn, productTokens } from "@/foundation/ui";
import { errorMessage } from "@/foundation/hooks";
import { formatMoney } from "@/foundation/format";
import { hasCode } from "@/foundation/platform-client";
import { startCheckout, type Plan } from "@/capabilities/account/api";
import { CONSENT_DOCUMENT, CONSENT_REQUIRED } from "@/capabilities/account/settings/checkoutConsent";

const { b2cLink } = productTokens;

/**
 * The retiring client's `PLAN_TYPE_LABELS` and its blurb per plan, keyed by
 * the months a plan runs for. A plan sold for some other length falls back to
 * its own duration, so a new plan in Stripe still gets a sentence.
 */
const PLAN_COPY: Record<number, { title: string; description: string }> = {
  1: {
    title: "1-Month Access",
    description: "50 stations · last-minute preparation",
  },
  3: {
    title: "3-Month Access",
    description: "100 stations · long-term preparation",
  },
  6: {
    title: "6-Month Access",
    description: "150 stations · best value",
  },
};

/** The old picker opened on the three-month plan. */
const DEFAULT_MONTHS = 3;

/**
 * Pick a plan, and pay for it.
 *
 * The retiring client's `PaymentsUpgrade`, string for string. It is the only
 * way anybody buys anything, so what it does and does not do both matter. It
 * sends a **plan code** — never a price — and then hands the browser to
 * Stripe's hosted page; no card detail passes through here, and nothing in
 * this file can grant access. The plans, their prices and their durations are
 * the backend's answer to `/billing/plans` rather than constants compiled into
 * the bundle, which is how the retiring client came to show one price and
 * charge another after a change in Stripe.
 *
 * One field the old picker did not have: a friend's referral code. The old
 * client took it at sign-up; `platform-api` takes it only at checkout
 * (`CheckoutStart.referral_code`), so without this box nobody could redeem
 * one. Typing a code shows each plan's 10%-off price, but only the backend
 * decides whether the code is good.
 */
export default function PlanPicker({
  plans,
  variant = "page",
}: {
  plans: Plan[];
  variant?: "modal" | "page";
}) {
  const [selected, setSelected] = useState<string | null>(defaultPlanCode(plans));
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
      setError(CONSENT_REQUIRED);
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

  return (
    <ModalContent className="w-full">
      {/* On the settings page the card's own title says this. */}
      {variant === "modal" ? (
        <ModalHelper className="mb-5 mt-0">Choose the option that suits you best</ModalHelper>
      ) : null}

      <div role="radiogroup" aria-label="Plan" className="grid gap-3 sm:grid-cols-3">
        {plans.map((plan) => {
          const isSelected = selected === plan.code;
          return (
            <button
              key={plan.code}
              type="button"
              role="radio"
              aria-checked={isSelected}
              onClick={() => setSelected(plan.code)}
              className={cn(
                "flex items-start gap-3 rounded-osce-lg border px-4 py-3.5 text-left transition",
                // The selected tile's border is 2px; a ring of the same colour
                // adds the second pixel without moving the text.
                isSelected
                  ? "border-accent bg-osce-accent-subtle ring-1 ring-accent"
                  : "border-border bg-surface hover:bg-canvas",
              )}
            >
              <span className="min-w-0 flex-1">
                <span className="block text-osce-body font-medium text-ink">{planTitle(plan)}</span>
                <span className="mt-0.5 block text-osce-meta text-ink-muted">{planDescription(plan)}</span>
                <span className="mt-2 flex items-baseline gap-2 text-osce-body font-semibold text-ink">
                  <PlanPrice plan={plan} hasReferralCode={hasReferralCode} />
                </span>
              </span>
              <span
                className={cn(
                  "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border",
                  isSelected ? "border-accent" : "border-border",
                )}
                aria-hidden
              >
                {isSelected ? <span className="h-2.5 w-2.5 rounded-full bg-accent" /> : null}
              </span>
            </button>
          );
        })}
      </div>

      <div className="mt-6">
        <Input
          id="checkout-referral-code"
          label="Friend's referral code"
          hint="Optional."
          value={referralCode}
          onChange={(event) => setReferralCode(event.target.value)}
          placeholder="Enter a code for 10% off"
          autoComplete="off"
          maxLength={32}
        />
      </div>

      <Checkbox
        id="policies"
        className="mt-6"
        checked={agreedToPolicies}
        onChange={() => setAgreedToPolicies(!agreedToPolicies)}
        label={
          <>
            I agree to the{" "}
            <a
              href="/compliances/terms-of-service"
              target="_blank"
              rel="noreferrer"
              className={b2cLink}
            >
              {CONSENT_DOCUMENT}
            </a>{" "}
            (including our No Refund Policy)
          </>
        }
      />

      <div className="mt-6 space-y-3">
        <div className="flex sm:justify-end">
          <Button
            onClick={() => void handleCheckout()}
            disabled={isLoading || !chosen}
            className="w-full gap-2 whitespace-nowrap sm:w-auto"
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
                  Upgrade now
                  {chosen
                    ? ` · ${formatMoney(chargedPence(chosen, hasReferralCode), chosen.currency)}`
                    : ""}
                </span>
              </>
            )}
          </Button>
        </div>
        {error ? <p className="text-osce-meta text-danger sm:text-right">{error}</p> : null}
        <p className="text-osce-meta text-ink-muted sm:text-right">Secure payment powered by Stripe</p>
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
      <s className="font-normal text-ink-muted">{formatMoney(plan.amount_pence, plan.currency)}</s>
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
function planMonths(plan: Plan): number {
  return Math.round(plan.duration_days / 30);
}

/** The three-month plan when it is on sale, else the first one, as the old picker did. */
function defaultPlanCode(plans: Plan[]): string | null {
  const preferred = plans.find((plan) => planMonths(plan) === DEFAULT_MONTHS);
  return preferred?.code ?? plans[0]?.code ?? null;
}

export function planTitle(plan: Plan): string {
  const months = planMonths(plan);
  return PLAN_COPY[months]?.title ?? (months >= 1 ? `${months}-Month Access` : `${plan.duration_days}-Day Access`);
}

export function planDescription(plan: Plan): string {
  return PLAN_COPY[planMonths(plan)]?.description ?? `${plan.duration_days} days of practice`;
}
