import type { ReactNode } from "react";
import type { IconType } from "react-icons";
import {
  B2CPanelCard,
  B2CPanelCardBody,
  B2CPanelCardHeader,
  B2CSectionIconBadge,
  cn,
  productTokens,
  type B2CSectionIconTone,
} from "@/foundation/ui";

/** Lines body copy up with the section title, after the badge and its gap. */
export const doctorInfoContentInset = "pl-10";

/** A flat section of the brief: quiet chrome, readable body copy. */
export function DoctorInfoSection({
  title,
  icon,
  iconTone = "primary",
  children,
  className = "",
  emphasize = false,
}: {
  title: string;
  icon?: IconType;
  iconTone?: B2CSectionIconTone;
  children: ReactNode;
  className?: string;
  emphasize?: boolean;
}) {
  const Icon = icon;

  return (
    <section
      className={cn("space-y-2 border-b border-b2c-border pb-4 last:border-b-0 last:pb-0", className)}
    >
      <h3 className={cn(productTokens.b2cSectionTitle, "flex items-center gap-2")}>
        {Icon ? (
          <B2CSectionIconBadge tone={iconTone} className="shrink-0">
            <Icon aria-hidden />
          </B2CSectionIconBadge>
        ) : null}
        <span className="min-w-0 flex-1">{title}</span>
      </h3>
      <div
        className={cn(
          "text-osce-body leading-relaxed text-osce-ink-900",
          Icon && doctorInfoContentInset,
          emphasize &&
            (Icon
              ? "border-l-2 border-osce-accent pl-[calc(2.5rem+0.75rem)]"
              : "border-l-2 border-osce-accent pl-3"),
        )}
      >
        {children}
      </div>
    </section>
  );
}

/** Disc bullets for the reading lists. Nothing at all when there is nothing. */
export function DoctorInfoBulletList({
  items,
  className = "",
}: {
  items: string[] | undefined | null;
  className?: string;
}) {
  if (!items?.length) return null;

  return (
    <ul className={cn("space-y-2", className)}>
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  );
}

/**
 * One outer panel when the brief stands alone, plain content when it is the
 * right-hand column of the consultation screen.
 */
export function DoctorInfoShell({
  embedded = false,
  title,
  children,
}: {
  embedded?: boolean;
  title: string;
  children: ReactNode;
}) {
  if (embedded) {
    return <div className="space-y-4 p-4 sm:p-5">{children}</div>;
  }

  return (
    <B2CPanelCard className="mt-0">
      <B2CPanelCardHeader>{title}</B2CPanelCardHeader>
      <B2CPanelCardBody className="space-y-4">{children}</B2CPanelCardBody>
    </B2CPanelCard>
  );
}
