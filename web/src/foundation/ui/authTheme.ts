import { landingAccent } from "@/foundation/ui/landingTheme";

/** Auth route shell — sky marketing canvas + white card (data-b2c-auth + data-b2c-landing-surface="cream"). */
export const authCanvas =
  "bg-landing-canvas bg-[radial-gradient(55rem_34rem_at_12%_4%,var(--landing-bloom-warm,transparent)_0%,transparent_62%),radial-gradient(48rem_30rem_at_88%_18%,var(--landing-bloom-soft,transparent)_0%,transparent_60%)] bg-no-repeat";

export const authCard =
  "rounded-landing-card border border-landing-warm bg-landing-card p-6 shadow-landing-soft sm:p-[26px]";

export const authTitle =
  "font-landing-heading text-osce-title font-semibold tracking-[-0.02em] text-osce-ink-900";

export const authSubtitle =
  "mt-2 font-landing-body text-osce-body leading-relaxed text-b2c-text-secondary";

export const authEyebrow =
  "font-landing-mono text-osce-micro font-medium uppercase tracking-[0.13em] text-b2c-text-muted";

export const authEyebrowPill =
  "inline-flex items-center rounded border border-osce-accent-subtle bg-osce-accent-muted px-3 py-1 font-landing-mono text-osce-micro font-medium uppercase tracking-[0.08em] text-osce-accent-hover";

export const authLink =
  "font-medium text-osce-accent transition-colors hover:text-osce-accent-hover";

export const authButtonPrimary = landingAccent.btn;

export const authInput =
  "w-full rounded-landing-card border border-landing-warm bg-landing-card px-4 py-3 text-osce-body text-osce-ink-900 placeholder:text-b2c-text-muted focus:border-osce-accent focus:outline-none focus-visible:ring-2 focus-visible:ring-osce-accent/30 focus-visible:ring-offset-0";

export const authLabel =
  "block text-osce-meta font-medium text-b2c-text-secondary";

export const authHeader =
  "sticky top-0 z-10 shrink-0 border-b border-landing-hairline bg-landing-nav backdrop-blur-[10px]";

export const authFooterLink =
  "text-center font-landing-body text-osce-body text-b2c-text-secondary";

export const authQuoteBody =
  "font-landing-body text-osce-data leading-relaxed text-b2c-text-secondary sm:leading-[1.6]";
