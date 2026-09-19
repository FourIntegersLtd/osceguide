import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/foundation/ui/cn";

// `title` is widened to ReactNode, so it has to be taken off the DOM props
// it would otherwise conflict with (where it is the tooltip attribute).
export interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  title?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}

export function Card({ title, description, actions, className, children, ...rest }: CardProps) {
  return (
    <section
      className={cn("rounded-panel border border-border bg-surface", className)}
      {...rest}
    >
      {(title || actions) && (
        <header className="flex items-start justify-between gap-4 border-b border-border px-5 py-4">
          <div className="min-w-0">
            {title && <h2 className="truncate text-base font-semibold text-ink">{title}</h2>}
            {description && <p className="mt-1 text-sm text-ink-muted">{description}</p>}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </header>
      )}
      {children && <div className="px-5 py-4">{children}</div>}
    </section>
  );
}
