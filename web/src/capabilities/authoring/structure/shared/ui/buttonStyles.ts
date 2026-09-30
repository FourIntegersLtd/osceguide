/**
 * Pure class-string composition for Button. Split out of Button.tsx so the
 * node --test runner can import it: the runner strips types but cannot
 * transform JSX, so anything reachable from a test has to stay JSX-free.
 */
import { cn } from "@/capabilities/authoring/structure/shared/lib/utils";

export type ButtonVariant =
  | "primary"
  | "commit"
  | "secondary"
  | "danger"
  | "dangerSolid"
  | "outline"
  | "ghost";

export type ButtonSize = "xs" | "sm" | "md" | "lg" | "hero";

export interface ButtonStyleProps {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  themeType?: "b2c" | "b2b";
  className?: string;
}

const baseButtonStyles =
  "inline-flex items-center justify-center font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-60 disabled:pointer-events-none";

/**
 * The black CTA, shared by both arms — though they read it differently.
 *
 * In B2C it is the top of a ladder: blue is the ordinary primary and black is
 * reserved for the one committing action on a screen. In B2B it *is* the
 * primary (92 call sites against 8 blue ones), and blue demotes to accent and
 * links. Same colour, opposite frequency; see `src/b2b/theme/b2bUi.ts`.
 *
 * Rest sits at ink-800 rather than ink-900 so the hover has somewhere to go:
 * there is no room to darken below #101828 (even pure black is a 1.18 step,
 * under blue's 1.30), whereas ink-800 -> ink-900 is 1.21 and reads correctly.
 *
 * `!text-white` (rather than plain `text-white`) beats LiveKit's theme vars —
 * see the note on `danger` below. Dark text on a black button is a total
 * failure mode, so the `!` stays even though it is rarely needed.
 *
 * The focus ring stays blue: ring colour is a system-wide affordance, and a
 * black ring on a black button with `ring-offset-1` reads as a thicker border,
 * not a focus state.
 */
const commitStyles =
  "bg-ink !text-white hover:bg-ink focus:ring-osce-accent/40 border border-transparent";

const b2cVariants: Record<ButtonVariant, string> = {
  primary:
    "bg-osce-accent !text-white hover:bg-osce-accent-hover focus:ring-osce-accent/30 border border-transparent",
  commit: commitStyles,
  secondary:
    "bg-osce-surface border border-border text-ink hover:bg-surface-raised focus:ring-osce-accent/20",
  danger:
    // !bg / !text beat LiveKit `.lk-disconnect-button` Theme vars (otherwise invisible on white)
    "!bg-osce-danger !text-white hover:!bg-osce-danger-hover focus:ring-osce-danger border border-transparent",
  dangerSolid:
    "!bg-osce-danger !text-white hover:!bg-osce-danger-hover focus:ring-osce-danger-border border border-transparent",
  outline:
    "border border-border text-ink hover:bg-surface-raised focus:ring-osce-accent/20 bg-osce-surface",
  ghost:
    "text-ink-subtle hover:bg-surface-raised hover:text-ink focus:ring-osce-accent/20 bg-transparent border border-transparent",
};

const b2bPrimaryStyles =
  "bg-accent text-white hover:bg-accent-hover focus:ring-accent/30 border border-transparent";

const b2bVariants: Record<ButtonVariant, string> = {
  primary: b2bPrimaryStyles,
  commit: commitStyles,
  secondary:
    "bg-white border border-border text-ink hover:bg-surface-raised focus:ring-ink/10",
  danger:
    "bg-white border border-danger/30 text-danger hover:bg-osce-danger-bg focus:ring-danger/30",
  dangerSolid:
    "bg-osce-danger text-white hover:bg-osce-danger-hover focus:ring-osce-danger-border border border-transparent",
  outline:
    "bg-white border border-border text-ink hover:bg-surface-raised focus:ring-ink/10",
  ghost:
    "text-ink-muted hover:bg-surface-raised hover:text-ink focus:ring-ink/10 bg-transparent border border-transparent",
};

/*
 * Buttons are a touch target before they are a rectangle: every size is at
 * least 44px tall below `sm` (WCAG 2.5.5 / the iOS minimum) and relaxes to
 * its denser desktop height from `sm` up. The height grows rather than
 * hiding an invisible ::after hit area, because a hit area nothing renders
 * is one nobody notices breaking.
 */
const b2cSizes: Record<ButtonSize, string> = {
  xs: "h-9 sm:h-7 px-2.5 text-osce-caption rounded-osce-md",
  sm: "h-10 sm:h-8 px-3 text-osce-body rounded-osce-md",
  md: "h-11 sm:h-9 px-4 text-osce-body rounded-osce-md",
  lg: "h-11 sm:h-10 px-5 text-osce-body rounded-osce-md",
  hero: "h-12 sm:h-11 px-6 text-osce-body font-medium rounded-osce-md w-full gap-2",
};

const b2bSizes: Record<ButtonSize, string> = {
  xs: "h-9 sm:h-7 px-2.5 text-osce-caption rounded-osce-md",
  sm: "h-10 sm:h-8 px-3 text-osce-body rounded-osce-md",
  md: "h-11 sm:h-9 px-4 text-osce-body rounded-osce-md",
  lg: "h-11 sm:h-10 px-5 text-osce-body rounded-osce-md",
  hero: "h-12 sm:h-11 px-6 text-osce-body font-medium rounded-osce-md w-full gap-2",
};

export function getButtonClassName({
  variant = "primary",
  size = "md",
  fullWidth = false,
  themeType = "b2c",
  className,
}: ButtonStyleProps = {}) {
  const variants = themeType === "b2b" ? b2bVariants : b2cVariants;
  const sizes = themeType === "b2b" ? b2bSizes : b2cSizes;

  return cn(
    baseButtonStyles,
    variants[variant],
    sizes[size],
    fullWidth && "w-full",
    className,
  );
}
