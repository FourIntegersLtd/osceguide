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
import { startCheckout, type Plan } from "@/capabilities/account/api";

const { b2cLink } = productTokens;

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

  const chosen = plans.find((plan) => plan.code === selected) ?? null;

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
      const { checkout_url } = await startCheckout(chosen.code);
      // Leave `isLoading` true: the browser is on its way to Stripe, and a
      // button that springs back to "Upgrade" invites a second checkout.
      window.location.assign(checkout_url);
    } catch (cause) {
      setError(
        `${errorMessage(cause)} No money has left your account. Please try again or email ${SUPPORT_EMAIL}.`,
      );
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
                {formatMoney(plan.amount_pence, plan.currency)}
              </span>
            </button>
          );
        })}
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
                  {chosen ? ` · ${formatMoney(chosen.amount_pence, chosen.currency)}` : ""}
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
