/*
 * Class strings for the sign-in pages. The card, fields and buttons are the board kit's
 * (`boardKit.ts`: docs/institution-overhaul/boards/SignIn.dc.html); only the page frame
 * (`authHeader`) is the public site's `.site-root` skin, which the auth layout carries.
 */

/** The card's title: the boards draw a sign-in screen at 26px, 600, and a short state card ("Choose a new password", "This link is incomplete") as a 16px h2. */
export const authTitle = (compact = false) =>
  compact ? "m-0 text-assess-state-title font-semibold text-osce-ink-900" : "my-1.5 text-assess-card-title font-semibold text-osce-ink-900";

/** The line under the title: the board's `.meta` (13px), or `lead` for the 14px the invitation and set-up screens use. */
export const authSubtitle = (lead = false) => `m-0 ${lead ? "text-assess-label" : "text-assess-meta"} leading-normal text-osce-ink-500`;

export const authLink =
  "text-osce-accent transition-colors hover:text-osce-accent-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-osce-accent";

/** Text under a form: "Already have an account?", "Send again" (the board's `.meta`). */
export const authFooterLink = "text-assess-meta leading-normal text-osce-ink-500";

export const authHeader = "border-b border-site-line bg-site-card";
