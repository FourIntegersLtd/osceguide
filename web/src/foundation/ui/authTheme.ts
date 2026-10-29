/*
 * Class strings for the sign-in pages, on the public site's `.site-root` tokens
 * (blue, light and dark). The auth layout carries `.site-root`; nothing here is
 * a colour of its own.
 */

export const authCard =
  "rounded-[22px] border border-site-line bg-site-card p-6 shadow-[0_18px_40px_-24px_rgba(14,42,92,0.35)] sm:p-9";

export const authTitle =
  "font-landing-heading text-[28px] font-bold leading-[1.15] tracking-tight text-site-ink sm:text-3xl";

export const authSubtitle = "mt-2 text-base leading-relaxed text-site-muted";

export const authLink =
  "font-semibold text-site-brand transition-colors hover:text-site-brand-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-site-brand";

/** Text under a form: "Already have an account?", "Send again". */
export const authFooterLink = "text-center text-[15px] leading-relaxed text-site-muted";

/** Field box. Padding-left is added by the field, which knows whether it has an icon. */
export const authInput =
  "w-full min-h-[50px] rounded-xl border border-site-rule bg-site-card py-3 pr-3.5 text-base text-site-ink placeholder:text-site-faint focus:border-site-brand focus:outline-none focus:ring-4 focus:ring-site-pale";

export const authLabel = "block text-sm font-semibold text-site-ink";

export const authHeader = "border-b border-site-line bg-site-card";
