import React from "react";
import { cn } from "@/foundation/ui/cn";

export interface CardProps extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  themeType?: "b2c" | "b2b";
  padding?: "none" | "sm" | "md" | "lg";
  /** Renders a bordered header. Ignored when the compound parts are used. */
  title?: React.ReactNode;
  description?: React.ReactNode;
  actions?: React.ReactNode;
}

export const cardPaddingMap = {
  none: "",
  sm: "p-4",
  md: "p-5 sm:p-6",
  lg: "p-6",
} as const;

/**
 * The canonical card surface — the single definition of "a card".
 *
 * Cards are flat: depth is a 1px border on a white surface over the canvas,
 * never a drop shadow. Genuinely floating surfaces — modals, toasts,
 * dropdowns — carry their own heavier shadow and are not cards.
 */
export function getCardSurfaceClasses({
  themeType = "b2c",
}: {
  themeType?: "b2c" | "b2b";
} = {}) {
  return themeType === "b2b"
    ? "rounded-lg border border-b2b-border bg-b2b-surface"
    : "rounded-osce-lg border border-b2c-border bg-osce-surface";
}

/**
 * Two ways to call this, both first-class.
 *
 * `<Card title=… actions=…>` is the short form, which most screens want and
 * which keeps a heading, a description and an action row consistent without
 * each screen re-laying them out. `<Card><CardHeader>…` is the compound form,
 * for the screens that need something the short form cannot express.
 *
 * They were two separate components in the two clients, which is how the same
 * card ended up with two different header paddings. One component, two entry
 * points, one set of borders.
 */
const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, themeType = "b2c", padding = "none", title, description, actions, children, ...props }, ref) => {
    const surface = getCardSurfaceClasses({ themeType });
    const ink = themeType === "b2b" ? "text-b2b-headline" : "text-osce-ink-900";
    const hasHeader = Boolean(title || actions);

    return (
      <div
        ref={ref}
        className={cn(surface, ink, !hasHeader && cardPaddingMap[padding], className)}
        {...props}
      >
        {hasHeader && (
          <header className="flex items-start justify-between gap-4 border-b border-b2c-border px-5 py-4">
            <div className="min-w-0">
              {title && (
                <h2 className="truncate text-osce-subheading font-semibold text-osce-ink-900">
                  {title}
                </h2>
              )}
              {description && (
                <p className="mt-1 text-osce-body text-b2c-text-muted">{description}</p>
              )}
            </div>
            {actions && <div className="shrink-0">{actions}</div>}
          </header>
        )}
        {children != null && (hasHeader ? <div className="px-5 py-4">{children}</div> : children)}
      </div>
    );
  },
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col space-y-1.5 p-6 pb-4", className)} {...props} />
  ),
);
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(
  ({ className, ...props }, ref) => (
    <h3
      ref={ref}
      className={cn(
        "font-heading text-osce-title font-semibold leading-none tracking-tight",
        className,
      )}
      {...props}
    />
  ),
);
CardTitle.displayName = "CardTitle";

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
  ),
);
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex items-center p-6 pt-0", className)} {...props} />
  ),
);
CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardTitle, CardContent, CardFooter };
