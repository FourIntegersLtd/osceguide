import React from "react";
import { cn } from "@/capabilities/authoring/structure/shared/lib/utils";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  themeType?: "b2c" | "b2b";
  padding?: "none" | "sm" | "md" | "lg";
}

export const cardPaddingMap = {
  none: "",
  sm: "p-4",
  md: "p-5 sm:p-6",
  lg: "p-6",
} as const;

/**
 * The canonical card surface — the single definition of "a card".
 * `b2cCardShell` / `b2cCard` in b2cUi.ts and `b2bCard` in b2bUi.ts are all
 * built from this.
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

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  (
    {
      className,
      themeType = "b2c",
      padding = "none",
      ...props
    },
    ref,
  ) => {
    const surface = getCardSurfaceClasses({ themeType });
    const ink = themeType === "b2b" ? "text-b2b-headline" : "text-osce-ink-900";

    return (
      <div
        ref={ref}
        className={cn(surface, ink, cardPaddingMap[padding], className)}
        {...props}
      />
    );
  },
);
Card.displayName = "Card";

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6 pb-4", className)}
    {...props}
  />
));
CardHeader.displayName = "CardHeader";

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, children, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "font-heading text-osce-title font-semibold leading-none tracking-tight",
      className,
    )}
    {...props}
  >
    {children}
  </h3>
));
CardTitle.displayName = "CardTitle";

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
));
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
));
CardFooter.displayName = "CardFooter";

export { Card, CardHeader, CardTitle, CardContent, CardFooter };
