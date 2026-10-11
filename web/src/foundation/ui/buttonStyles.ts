/**
 * Pure class-string composition for Button. Split out of Button.tsx so the
 * node --test runner can import it: the runner strips types but cannot
 * transform JSX, so anything reachable from a test has to stay JSX-free.
 */
import { cn } from "@/foundation/ui/cn";

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
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-60 disabled:pointer-events-none";

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
 * Train's quiet skin has one primary colour, so there `--osce-commit` points
 * at the accent and the two tiers merge (tokens.css).
 *
 * The focus ring stays blue: ring colour is a system-wide affordance, and a
 * black ring on a black button with `ring-offset-1` reads as a thicker border,
 * not a focus state.
 */
const commitStyles =
  "bg-osce-commit !text-white hover:bg-osce-commit-hover focus:ring-osce-accent/40 border border-transparent";

/** Quiet bordered button: hairline border, ink text, a neutral fill on hover. */
const b2cBorderedStyles =
  "border border-b2c-border bg-osce-surface text-osce-ink-900 hover:bg-b2c-secondary focus:ring-osce-accent/20";

const b2cVariants: Record<ButtonVariant, string> = {
  primary:
    "bg-osce-accent !text-white hover:bg-osce-accent-hover focus:ring-osce-accent/30 border border-transparent",
  commit: commitStyles,
  secondary: b2cBorderedStyles,
  danger:
    // !bg / !text beat LiveKit `.lk-disconnect-button` Theme vars (otherwise invisible on white)
    "!bg-osce-danger !text-white hover:!bg-osce-danger-hover focus:ring-osce-danger border border-transparent",
  dangerSolid:
    "!bg-osce-danger !text-white hover:!bg-osce-danger-hover focus:ring-osce-danger-border border border-transparent",
  outline: b2cBorderedStyles,
  ghost:
    "text-b2c-text-muted hover:bg-b2c-secondary hover:text-osce-ink-900 focus:ring-osce-accent/20 bg-transparent border border-transparent",
};

const b2bPrimaryStyles =
  "bg-b2b-accent text-white hover:bg-b2b-accent-hover focus:ring-b2b-accent/30 border border-transparent";

const b2bVariants: Record<ButtonVariant, string> = {
  primary: b2bPrimaryStyles,
  commit: commitStyles,
  secondary:
    "bg-white border border-b2b-border text-b2b-headline hover:bg-b2b-cream focus:ring-b2b-headline/10",
  danger:
    "bg-white border border-b2b-danger/30 text-b2b-danger hover:bg-osce-danger-bg focus:ring-b2b-danger/30",
  dangerSolid:
    "bg-osce-danger text-white hover:bg-osce-danger-hover focus:ring-osce-danger-border border border-transparent",
  outline:
    "bg-white border border-b2b-border text-b2b-headline hover:bg-b2b-cream focus:ring-b2b-headline/10",
  ghost:
    "text-b2b-mid hover:bg-b2b-cream hover:text-b2b-headline focus:ring-b2b-headline/10 bg-transparent border border-transparent",
};

/*
 * Buttons are a touch target before they are a rectangle: every size is at
 * least 44px tall below `sm` (WCAG 2.5.5 / the iOS minimum) and relaxes to
 * its denser desktop height from `sm` up. The height grows rather than
 * hiding an invisible ::after hit area, because a hit area nothing renders
 * is one nobody notices breaking.
 */
/*
 * The canvas button is 36px, 14px type, radius 9 (`rounded-control`, which
 * each arm sets). `sm` is the 30px toolbar size.
 */
const b2cSizes: Record<ButtonSize, string> = {
  xs: "h-9 sm:h-7 px-2.5 text-osce-meta rounded-control",
  sm: "h-10 sm:h-[30px] px-2.5 text-[13px] rounded-control",
  md: "h-11 sm:h-9 px-3.5 text-osce-body rounded-control",
  lg: "h-11 sm:h-10 px-4 text-osce-body rounded-control",
  hero: "h-12 sm:h-10 px-5 text-osce-body font-medium rounded-control w-full",
};

const b2bSizes: Record<ButtonSize, string> = {
  xs: "h-9 sm:h-7 px-2.5 text-osce-caption rounded-md",
  sm: "h-10 sm:h-8 px-3 text-osce-body rounded-md",
  md: "h-11 sm:h-9 px-4 text-osce-body rounded-md",
  lg: "h-11 sm:h-10 px-5 text-osce-body rounded-md",
  hero: "h-12 sm:h-11 px-6 text-osce-body font-medium rounded-md w-full gap-2",
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
