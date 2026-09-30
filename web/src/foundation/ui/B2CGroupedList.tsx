import Link from "next/link";
import type { ReactNode } from "react";
import { HiChevronRight } from "react-icons/hi2";
import {
  b2cEyebrow,
  b2cGroupedRow,
  b2cGroupedRowSubtitle,
  b2cGroupedRowTitle,
  b2cGroupedShell,
} from "@/foundation/ui/productTokens";
type GroupedSectionProps = {
  eyebrow: string;
  children: ReactNode;
  sectionClassName?: string;
  className?: string;
};
export function B2CGroupedSection({
  eyebrow,
  children,
  sectionClassName = "mt-8",
  className = "",
}: GroupedSectionProps) {
  return (
    <section
      className={[sectionClassName, className].filter(Boolean).join(" ")}
    >
      {" "}
      <div className="mb-3 px-1">
        {" "}
        <p className={b2cEyebrow}>{eyebrow}</p>{" "}
      </div>{" "}
      <div className={b2cGroupedShell}>{children}</div>{" "}
    </section>
  );
}
type GroupedRowLinkProps = {
  href: string;
  title: string;
  subtitle?: string;
  trailing?: ReactNode;
  className?: string;
};
export function B2CGroupedRowLink({
  href,
  title,
  subtitle,
  trailing,
  className = "",
}: GroupedRowLinkProps) {
  return (
    <Link
      href={href}
      className={[b2cGroupedRow, className].filter(Boolean).join(" ")}
    >
      {" "}
      <div className="min-w-0 flex-1">
        {" "}
        <p className={b2cGroupedRowTitle}>{title}</p>{" "}
        {subtitle ? (
          <p className={b2cGroupedRowSubtitle}>{subtitle}</p>
        ) : null}{" "}
      </div>{" "}
      {trailing}{" "}
      <HiChevronRight
        className="h-4 w-4 shrink-0 text-b2c-text-muted"
        aria-hidden
      />{" "}
    </Link>
  );
}
