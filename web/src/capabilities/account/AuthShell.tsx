import type { ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";
import { authSubtitle, authTitle } from "@/foundation/ui/authTheme";
import { boardPad } from "@/foundation/ui/boardKit";

type AuthShellProps = {
  title: string;
  subtitle?: string;
  /** The subtitle at 14px (the invitation and set-up screens) instead of the 13px meta line. */
  lead?: boolean;
  /** A short state card: its title is the board's 16px h2 rather than the 26px sign-in title. */
  compact?: boolean;
  /** `split` is the card beside the navy panel (`sidePanel`); `card` is the card alone. */
  variant: "split" | "card";
  children: ReactNode;
  sidePanel?: ReactNode;
  className?: string;
};

/**
 * The sign-in card, drawn as the SignIn board's `.card.pad`: 460px, 20px padding and 14px between
 * its parts. It wears the assess skin's tokens (`data-surface`) though the page around it is the
 * public site's, so every sign-in screen is the same card.
 */
export default function AuthShell({ title, subtitle, lead = false, compact = false, variant, children, sidePanel, className }: AuthShellProps) {
  const card = (
    <section data-surface="assess" className={cn("w-full min-w-0 max-w-[460px] self-start justify-self-center text-osce-ink-900", boardPad)}>
      <h1 className={authTitle(compact)}>{title}</h1>
      {subtitle ? <p className={authSubtitle(lead)}>{subtitle}</p> : null}
      {children}
    </section>
  );

  if (variant === "split") {
    return (
      <div
        className={cn(
          "mx-auto grid w-full max-w-[1120px] flex-1 grid-cols-1 items-stretch gap-10 min-[961px]:grid-cols-[minmax(0,460px)_minmax(0,1fr)]",
          className,
        )}
      >
        {card}
        {sidePanel}
      </div>
    );
  }

  return <div className={cn("mx-auto w-full max-w-[460px] flex-1", className)}>{card}</div>;
}
