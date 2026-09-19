import { cn } from "@/shared/lib/utils";

interface LogoProps {
  variant?: "light" | "dark" | "ink";
  /** Collapsed sidebar — blue Guide mark only */
  compact?: boolean;
  className?: string;
  /** When false, renders static branding (use inside another button or control). */
  interactive?: boolean;
}

const guideArrowClip =
  "[clip-path:polygon(0_0,calc(100%-16px)_0,100%_50%,calc(100%-16px)_100%,0_100%)]";

export default function Logo({
  variant = "light",
  compact = false,
  className = "",
  interactive = true,
}: LogoProps) {
  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const Wrapper = interactive ? "button" : "div";
  const wrapperProps = interactive
    ? {
        type: "button" as const,
        onClick: scrollToTop,
        id: "logo",
        "aria-label": "OSCE Guide home",
      }
    : { "aria-hidden": true };

  const isInk = variant === "ink";
  const useBrandBlue = variant === "light" || variant === "dark";

  const osceTextClass =
    variant === "dark"
      ? "text-white"
      : isInk
        ? "text-osce-ink-900"
        : "text-osce-accent";

  const guideBadgeClass = useBrandBlue
    ? "inline-flex items-center bg-osce-accent font-heading text-white"
    // Brand mark, not a button: the black-CTA guard only knows
    // "dark background + white text", which this legitimately is.
    // eslint-disable-next-line no-restricted-syntax
    : "inline-flex items-center bg-osce-ink-900 font-heading text-white";

  if (compact) {
    return (
      <Wrapper
        {...wrapperProps}
        className={cn(
          "flex h-10 w-10 items-center justify-center rounded-lg",
          interactive &&
            "cursor-pointer transition-opacity hover:bg-osce-accent-muted hover:opacity-90",
          className,
        )}
      >
        <span
          className={cn(
            guideBadgeClass,
            "h-9 min-w-9 justify-center pl-2 pr-5 text-osce-body font-bold",
            guideArrowClip,
          )}
        >
          G
        </span>
      </Wrapper>
    );
  }

  return (
    <Wrapper
      {...wrapperProps}
      className={cn(
        "flex items-center gap-2 px-1",
        interactive && "cursor-pointer transition-opacity hover:opacity-90",
        className,
      )}
    >
      <span
        className={cn(
          "font-heading text-osce-title font-bold",
          osceTextClass,
        )}
      >
        OSCE
      </span>
      <span
        className={cn(
          guideBadgeClass,
          "h-8 pl-2.5 pr-6",
          guideArrowClip,
        )}
      >
        <span className="text-osce-title font-bold">Guide</span>
      </span>
    </Wrapper>
  );
}
