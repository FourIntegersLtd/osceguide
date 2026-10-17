"use client";

import { useState } from "react";
import { PiSparkle } from "react-icons/pi";
import { Button, Checkbox, Input, ModalContent, ModalHelper, cn, productTokens, Spinner } from "@/foundation/ui";
import { formatMoney } from "@/foundation/format";
import { SUPPORT_EMAIL } from "@/foundation/support";
import { startCheckout, type Plan } from "@/capabilities/account/api";
import { checkoutErrorMessage } from "@/capabilities/account/settings/checkoutErrors";
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
    description: "Last-minute preparation",
  },
  3: {
    title: "3-Month Access",
    description: "Long-term preparation",
  },
  6: {
    title: "6-Month Access",
    description: "Best value",
  },
};

/** What every plan is, said once above the picker: fixed terms, paid once, nothing renews. */
export const UPGRADE_LEAD =
  "Choose how long you want full access for. Every option is a one-off payment, not a subscription";

/** The old picker opened on the three-month plan. */
const DEFAULT_MONTHS = 3;

/**
 * Pick a plan, and pay for it.
 *
 * The retiring client's `PaymentsUpgrade`, string for string. It is the only
 * way anybody buys anything, so what it does and does not do both matter. It
 * sends a **plan code** — never a price — and then opens Stripe's hosted page
 * in a new tab; no card detail passes through here, and nothing in
 * this file can grant access. The plans, their prices and their durations are
 * the backend's answer to `/billing/plans` rather than constants compiled into
 * the bundle, which is how the retiring client came to show one price and
 * charge another after a change in Stripe.
 *
 * One field the old picker did not have: a friend's referral code. The old
 * client took it at sign-up; `platform-api` takes it only at checkout
 * (`CheckoutStart.referral_code`), so without this box nobody could redeem
 * one. Only the backend decides whether a code is good, so the prices shown
 * are always the full ones and Stripe's page shows what is charged.
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
  // One per visit, renewed after a refusal: see `startCheckout`.
  const [attemptId, setAttemptId] = useState(() => crypto.randomUUID());
  const [openedInTab, setOpenedInTab] = useState(false);

  const chosen = plans.find((plan) => plan.code === selected) ?? null;
  // Blank means "no code": the full price, and nothing sent to the backend.
  const trimmedReferralCode = referralCode.trim();
  const hasReferralCode = trimmedReferralCode.length > 0;
  // Once a payment tab is open the choice is frozen: a different plan or code would be a second
  // Stripe session, and paying in both tabs charges twice. "Choose again" unfreezes it on purpose.
  const locked = isLoading || openedInTab;

  const handleCheckout = async () => {
    setError(null);
    if (!agreedToPolicies) {
      setError(CONSENT_REQUIRED);
      return;
    }
    if (!chosen) return;

    // Opened now, inside the click, so a popup blocker lets it through; Stripe's
    // address is only known once the backend answers. Not `noopener`: that makes
    // `window.open` return null. The opener link is cut before navigating instead.
    const tab = window.open("", "_blank");
    if (tab) tab.opener = null;
    setIsLoading(true);
    setOpenedInTab(false);
    try {
      const { checkout_url } = await startCheckout(
        chosen.code,
        hasReferralCode ? trimmedReferralCode : null,
        attemptId,
      );
      if (tab) {
        tab.location.href = checkout_url;
        setOpenedInTab(true);
        setIsLoading(false);
      } else {
        // Blocked anyway: pay in this tab. Leave `isLoading` true, the browser is
        // on its way to Stripe and a button that springs back invites a second checkout.
        window.location.assign(checkout_url);
      }
    } catch (cause) {
      tab?.close();
      setError(checkoutErrorMessage(cause, SUPPORT_EMAIL));
      setAttemptId(crypto.randomUUID());
      setIsLoading(false);
    }
  };

  return (
    <ModalContent className="w-full">
      {/* On the settings page the Upgrade card's description says this. */}
      {variant === "modal" ? <ModalHelper className="mb-5 mt-0">{UPGRADE_LEAD}</ModalHelper> : null}

      <div role="radiogroup" aria-label="Plan" className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {plans.map((plan) => {
          const isSelected = selected === plan.code;
          return (
            <button
              key={plan.code}
              type="button"
              role="radio"
              aria-checked={isSelected}
              disabled={locked}
              onClick={() => setSelected(plan.code)}
              className={cn(
                "flex items-start gap-3 rounded-osce-lg border px-4 py-3.5 text-left transition disabled:cursor-not-allowed disabled:opacity-60",
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
                  {formatMoney(plan.amount_pence, plan.currency)}
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
          hint="Optional. A valid code takes 10% off on the payment page."
          value={referralCode}
          onChange={(event) => setReferralCode(event.target.value)}
          placeholder="Enter a code for 10% off"
          autoComplete="off"
          maxLength={32}
          disabled={locked}
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
            onClick={() => handleCheckout()}
            disabled={locked || !chosen}
            className="w-full gap-2 whitespace-nowrap sm:w-auto"
          >
            {isLoading ? (
              <>
                <Spinner size="sm" className="text-current" label="Processing" />
                <span>Processing...</span>
              </>
            ) : (
              <>
                <PiSparkle className="h-4 w-4 shrink-0" aria-hidden />
                <span>
                  Upgrade now
                  {chosen ? ` · ${formatMoney(chosen.amount_pence, chosen.currency)}` : ""}
                </span>
              </>
            )}
          </Button>
        </div>
        {error ? <p className="text-osce-meta text-danger sm:text-right">{error}</p> : null}
        {openedInTab ? (
          <p role="status" className="text-osce-meta text-ink sm:text-right">
            Payment opened in a new tab. Your plan updates here when you come back{" "}
            <button
              type="button"
              className={cn(b2cLink, "ml-2")}
              onClick={() => {
                setOpenedInTab(false);
                setAttemptId(crypto.randomUUID());
              }}
            >
              Choose again
            </button>
          </p>
        ) : null}
        <p className="text-osce-meta text-ink-muted sm:text-right">Secure payment powered by Stripe</p>
      </div>
    </ModalContent>
  );
}

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
