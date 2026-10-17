"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  HiOutlineCheckCircle,
  HiOutlineClock,
  HiOutlineXCircle,
} from "react-icons/hi2";
import { productTokens, Spinner } from "@/foundation/ui";
import { PERSONAL_SLUG, workspaceBasePath } from "@/foundation/routing";
import { useOptionalSurface } from "@/capabilities";
import { listEntitlements, listReceiptsForSession } from "@/capabilities/account/api";
import { latestLiveEnd } from "@/capabilities/account/access";
import { confirmPayment, type PaymentOutcome } from "@/capabilities/account/paymentConfirmation";
import { loginHref } from "@/foundation/session/loginHref";
import { SUPPORT_EMAIL } from "@/foundation/support";

const { b2cButtonPrimary, b2cButtonSecondary, b2cCardPlain, b2cGhostButton } = productTokens;

type ConfirmState = "confirming" | PaymentOutcome | "unknown";

/**
 * Where Stripe sends somebody who paid.
 *
 * It confirms rather than congratulates. Paying and being entitled are two
 * events — the checkout redirect happens in the browser, the grant happens
 * when Stripe's webhook reaches the backend — and they arrive in that order
 * with a gap between them. So this asks for the receipt of the very checkout
 * session in the address (`?session_id=`), and after six tries says "received,
 * being activated" instead of claiming access the person does not yet have.
 * Asking about entitlements instead would confirm a renewal or a trial the
 * moment the page opened. A buyer the API no longer recognises is asked to
 * sign in, not left on a message that cannot change.
 *
 * It renders outside any workspace shell, because the backend's `success_url`
 * is a fixed address on the site rather than one inside a workspace. That is
 * why the surface context is optional here: with no shell around it, the links
 * point at the person's own practice.
 */
export default function PaymentReturn() {
  const sessionId = useSearchParams().get("session_id");
  const [state, setState] = useState<ConfirmState>(sessionId ? "confirming" : "unknown");
  const [endsAt, setEndsAt] = useState<string | null>(null);
  const home = useHomeHref();

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    void (async () => {
      const outcome = await confirmPayment(
        () => listReceiptsForSession(sessionId),
        (ms) => new Promise((resolve) => window.setTimeout(resolve, ms)),
        () => cancelled,
      );
      if (cancelled) return;
      if (outcome === "paid") {
        // Best effort: the date is a nicety, the receipt is the proof.
        // eslint-disable-next-line no-restricted-syntax -- best effort: the end date is a nicety, the receipt is the proof
        const ends = await listEntitlements()
          .then(({ items }) => latestLiveEnd(items))
          .catch(() => null);
        if (cancelled) return;
        setEndsAt(ends);
      }
      setState(outcome);
    })();
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  return (
    <div className="flex min-h-[70dvh] items-center justify-center px-4">
      <div
        className={`${b2cCardPlain} w-full max-w-md p-8 text-center`}
        role="status"
        aria-live="polite"
      >
        <ReturnBody state={state} endsAt={endsAt} sessionId={sessionId} home={home} />
      </div>
    </div>
  );
}

/** What the card says for each outcome; one early return per state. */
function ReturnBody({
  state,
  endsAt,
  sessionId,
  home,
}: {
  state: ConfirmState;
  endsAt: string | null;
  sessionId: string | null;
  home: string;
}) {
  if (state === "confirming") {
    return (
      <>
        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-osce-lg bg-b2c-surface-muted">
          <Spinner size="md" label="Confirming" />
        </span>
        <h1 className="mb-2 text-osce-title font-semibold text-ink">Confirming your payment</h1>
        <p className="text-osce-body text-ink-subtle">This takes a few seconds. Please keep this page open.</p>
      </>
    );
  }
  if (state === "paid") {
    return (
      <>
        <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-osce-lg bg-b2c-surface-muted">
          <HiOutlineCheckCircle className="h-6 w-6 text-osce-success-text" aria-hidden />
        </span>
        <h1 className="mb-2 text-osce-title font-semibold text-ink">Payment confirmed</h1>
        <p className="mb-8 text-osce-body text-ink-subtle">
          {endsAt
            ? `Your access runs until ${formatDay(endsAt)}.`
            : "Your payment has been recorded and your access is active."}
        </p>
        <Link href={`${home}/dashboard`} className={b2cButtonPrimary}>
          Go to dashboard
        </Link>
      </>
    );
  }
  if (state === "signed_out") {
    return (
      <>
        <h1 className="mb-2 text-osce-title font-semibold text-ink">Sign in to see your payment</h1>
        <p className="mb-6 text-osce-body text-ink-subtle">
          We can only confirm a payment for the account that made it. Sign in and this page will check again.
        </p>
        <Link
          href={loginHref(`/billing/complete?session_id=${encodeURIComponent(sessionId ?? "")}`, true)}
          className={b2cButtonPrimary}
        >
          Sign in
        </Link>
      </>
    );
  }
  if (state === "unknown") {
    return (
      <>
        <h1 className="mb-2 text-osce-title font-semibold text-ink">Nothing to confirm here</h1>
        <p className="mb-6 text-osce-body text-ink-subtle">
          This page needs the link Stripe sends after a payment. Your plan and receipts are under Payments in
          your settings.
        </p>
        <Link href={`${home}/settings?tab=payments`} className={b2cButtonPrimary}>
          Go to payments
        </Link>
      </>
    );
  }
  return (
    <>
      <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-osce-lg bg-b2c-surface-muted">
        <HiOutlineClock className="h-6 w-6 text-osce-warning-icon" aria-hidden />
      </span>
      <h1 className="mb-2 text-osce-title font-semibold text-ink">Payment received</h1>
      <p className="mb-6 text-osce-body text-ink-subtle">
        Your access is being activated. This can take a minute. If it isn&apos;t active shortly, email{" "}
        <a href={`mailto:${SUPPORT_EMAIL}`} className="text-osce-accent underline">
          {SUPPORT_EMAIL}
        </a>{" "}
        and we&apos;ll sort it.
      </p>
      <div className="flex flex-wrap justify-center gap-3">
        <button type="button" onClick={() => window.location.reload()} className={b2cButtonSecondary}>
          Check again
        </button>
        <Link href={`${home}/dashboard`} className={b2cGhostButton}>
          Go to dashboard
        </Link>
      </div>
    </>
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
