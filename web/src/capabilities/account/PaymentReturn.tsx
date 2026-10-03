"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  HiOutlineArrowPath,
  HiOutlineCheckCircle,
  HiOutlineClock,
  HiOutlineXCircle,
} from "react-icons/hi2";
import { productTokens } from "@/foundation/ui";
import { PERSONAL_SLUG, workspaceBasePath } from "@/foundation/routing";
import { useOptionalSurface } from "@/capabilities";
import { listEntitlements } from "@/capabilities/account/api";
import { SUPPORT_EMAIL } from "@/capabilities/account/settings/PlanPicker";

const { b2cButtonPrimary, b2cButtonSecondary, b2cCardPlain, b2cGhostButton } = productTokens;

/** Stripe's webhook can land a beat after the redirect; poll briefly. */
const CONFIRM_ATTEMPTS = 6;
const CONFIRM_INTERVAL_MS = 2000;

type ConfirmState = "confirming" | "active" | "pending";

/**
 * Where Stripe sends somebody who paid.
 *
 * It confirms rather than congratulates. Paying and being entitled are two
 * events — the checkout redirect happens in the browser, the grant happens
 * when Stripe's webhook reaches the backend — and they arrive in that order
 * with a gap between them. So this asks `/me/entitlements` until a live grant
 * appears, and after six tries says "received, being activated" instead of
 * claiming access the person does not yet have.
 *
 * It renders outside any workspace shell, because the backend's `success_url`
 * is a fixed address on the site rather than one inside a workspace. That is
 * why the surface context is optional here: with no shell around it, the links
 * point at the person's own practice.
 */
export default function PaymentReturn() {
  const [state, setState] = useState<ConfirmState>("confirming");
  const [endsAt, setEndsAt] = useState<string | null>(null);
  const home = useHomeHref();

  useEffect(() => {
    let cancelled = false;
    let attempt = 0;
    let timer: number | undefined;

    const tick = async () => {
      attempt += 1;
      try {
        const { items } = await listEntitlements();
        // `live` and nothing else. The list carries revoked and expired rows
        // too, and reading it as "what I have" is how a revoked entitlement
        // went on unlocking stations in the old client.
        const live = items.find((entitlement) => entitlement.live);
        if (cancelled) return;
        if (live) {
          setEndsAt(live.ends_at);
          setState("active");
          return;
        }
      } catch {
        // A failed poll is not a failed payment. Keep trying, then fall
        // through to the "received" state, which is what is actually true.
      }
      if (cancelled) return;
      if (attempt >= CONFIRM_ATTEMPTS) {
        setState("pending");
        return;
      }
      timer = window.setTimeout(() => void tick(), CONFIRM_INTERVAL_MS);
    };

    void tick();
    return () => {
      cancelled = true;
      if (timer) window.clearTimeout(timer);
    };
  }, []);

  return (
    <div className="flex min-h-[70dvh] items-center justify-center px-4">
      <div
        className={`${b2cCardPlain} w-full max-w-md p-8 text-center`}
        role="status"
        aria-live="polite"
      >
        {state === "confirming" ? (
          <>
            <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-osce-lg bg-b2c-surface-muted">
              <HiOutlineArrowPath className="h-6 w-6 animate-spin text-osce-accent" aria-hidden />
            </span>
            <h1 className="mb-2 text-osce-title font-semibold text-ink">
              Confirming your payment
            </h1>
            <p className="text-osce-body text-ink-subtle">
              This takes a few seconds. Please keep this page open.
            </p>
          </>
        ) : state === "active" ? (
          <>
            <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-osce-lg bg-b2c-surface-muted">
              <HiOutlineCheckCircle className="h-6 w-6 text-osce-success-text" aria-hidden />
            </span>
            <h1 className="mb-2 text-osce-title font-semibold text-ink">
              You&apos;re all set
            </h1>
            <p className="mb-8 text-osce-body text-ink-subtle">
              {endsAt
                ? `Your plan is active until ${formatDay(endsAt)}.`
                : "Your plan is active. All stations are unlocked."}
            </p>
            <Link href={`${home}/dashboard`} className={b2cButtonPrimary}>
              Go to dashboard
            </Link>
          </>
        ) : (
          <>
            <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-osce-lg bg-b2c-surface-muted">
              <HiOutlineClock className="h-6 w-6 text-osce-warning-icon" aria-hidden />
            </span>
            <h1 className="mb-2 text-osce-title font-semibold text-ink">
              Payment received
            </h1>
            <p className="mb-6 text-osce-body text-ink-subtle">
              Your access is being activated. This can take a minute. If it isn&apos;t
              active shortly, email{" "}
              <a href={`mailto:${SUPPORT_EMAIL}`} className="text-osce-accent underline">
                {SUPPORT_EMAIL}
              </a>{" "}
              and we&apos;ll sort it.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <button
                type="button"
                onClick={() => window.location.reload()}
                className={b2cButtonSecondary}
              >
                Check again
              </button>
              <Link href={`${home}/dashboard`} className={b2cGhostButton}>
                Go to dashboard
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

/** Where Stripe sends somebody who changed their mind. Nothing was charged. */
export function CheckoutCancelled() {
  const home = useHomeHref();
  return (
    <div className="flex min-h-[70dvh] items-center justify-center px-4">
      <div className={`${b2cCardPlain} w-full max-w-md p-8 text-center`}>
        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-osce-lg bg-b2c-surface-muted">
              <HiOutlineXCircle className="h-6 w-6 text-ink-subtle" aria-hidden />
            </span>
        <h1 className="mb-2 text-osce-title font-semibold text-ink">
          Checkout cancelled
        </h1>
        <p className="mb-8 text-osce-body text-ink-subtle">
          No payment was taken. You can pick a plan again whenever you&apos;re ready.
        </p>
        <div className="flex flex-wrap justify-center gap-3">
          <Link href={`${home}/settings?tab=payments`} className={b2cButtonPrimary}>
            Back to plans
          </Link>
          <Link href={`${home}/dashboard`} className={b2cButtonSecondary}>
            Go to dashboard
          </Link>
        </div>
        <p className="mt-6 text-osce-meta text-ink-subtle">
          Had a problem paying?{" "}
          <a href={`mailto:${SUPPORT_EMAIL}`} className="text-osce-accent underline">
            Email us
          </a>
          .
        </p>
      </div>
    </div>
  );
}

/**
 * The workspace to go back to.
 *
 * These two pages are the only screens in the capability that can render with
 * no shell around them — Stripe returns to a fixed address, not to a
 * workspace — so the surface context is asked for rather than required, and a
 * person's own practice is the answer when there is none.
 */
function useHomeHref(): string {
  const surface = useOptionalSurface();
  return surface ? surface.basePath : workspaceBasePath(PERSONAL_SLUG);
}

function formatDay(value: string): string {
  const date = new Date(value);
  return Number.isFinite(date.getTime())
    ? date.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })
    : "";
}
