/**
 * Shared brand tokens. single source of truth for whitelabel accent + semantic colors.
 * Keep in sync with --brand-* CSS variables in globals.css (:root).
 *
 * Original OSCE Guide blue — Tailwind blue-600 scale.
 */
export const brandTokens = {
  primary: "#2563eb",
  primaryHover: "#1d4ed8",
  primaryMuted: "#eff6ff",
  primarySubtle: "#dbeafe",
  primaryLight: "#3b82f6",
  danger: "#ef4444",
  dangerHover: "#dc2626",
} as const;

/** RGB components of `primary` for shadow utilities. */
export const brandPrimaryRgb = "37, 99, 235" as const;

export type BrandTokens = typeof brandTokens;
