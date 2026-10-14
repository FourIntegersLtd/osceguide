import type { ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";
import { b2cHeroCtaSurface, b2cHeroTitle, b2cMonoEyebrow } from "@/foundation/ui/productTokens";

/**
 * The one hero per screen (canvas `train-dashboard`, `train-combine`): a grey
 * panel that says what the screen is for and carries its one action.
 */
export function B2CHero({
  eyebrow,
  title,
  children,
  action,
  aside,
  lead = false,
  as: Title = "h2",
  className,
}: {
  eyebrow?: ReactNode;
  title: ReactNode;
  /** One or two sentences under the title. */
  children?: ReactNode;
  action?: ReactNode;
  /** Small facts beside the copy, such as a session's duration (canvas `train-session`). */
  aside?: ReactNode;
  /** The larger title, for the hero that leads a whole page (canvas `train-dashboard`). */
  lead?: boolean;
  as?: "h1" | "h2";
  className?: string;
}) {
  return (
    <section
      className={cn(b2cHeroCtaSurface, "flex flex-col gap-5 md:flex-row md:items-center md:justify-between", className)}
    >
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        {eyebrow ? <p className={b2cMonoEyebrow}>{eyebrow}</p> : null}
        <Title
          className={
            lead ? cn("max-w-[640px]", b2cHeroTitle) : "text-balance text-osce-title font-semibold text-osce-ink-900"
          }
        >
          {title}
        </Title>
        {/* Capped only beside an aside; alone it runs the hero's full width. */}
        {children ? (
          <p className={cn("text-osce-body text-b2c-text-muted", aside && "max-w-[720px]")}>{children}</p>
        ) : null}
        {action ? <div className="mt-3.5 flex flex-wrap items-center gap-2">{action}</div> : null}
      </div>
      {aside ? <div className="flex shrink-0 gap-3">{aside}</div> : null}
    </section>
  );
}
