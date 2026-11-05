"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Fragment, type ReactNode } from "react";
import { MdLogout } from "react-icons/md";
import { AnchoredTooltip, cn } from "@/foundation/ui";
import { isNavActive } from "@/foundation/navigation/isNavActive";
import {
  b2cNavLinkActive,
  b2cNavLinkInactive,
  b2cNavSectionLabel,
  b2cNavTooltipArrow,
  b2cNavTooltipChip,
  b2cScrollY,
} from "@/foundation/ui/productTokens";
import type { NavSection } from "@/capabilities";
import type { NavItem } from "@/surfaces/contract";

export type NavRailGroups = {
  ungrouped: NavItem[];
  sections: { section: NavSection; label: string; items: NavItem[] }[];
};

function NavTooltip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <AnchoredTooltip
      label={label}
      placement="right"
      chipClassName={b2cNavTooltipChip}
      className="w-full"
      chipDecoration={<span className={b2cNavTooltipArrow} />}
    >
      {children}
    </AnchoredTooltip>
  );
}

export function NavRailList({
  groups,
  basePath,
  collapsed,
  onNavigate,
  onSignOut,
  ariaLabel,
  footer,
  className,
}: {
  groups: NavRailGroups;
  basePath: string;
  collapsed: boolean;
  onNavigate: () => void;
  /** Omitted when the shell puts sign-out somewhere else (train's user row). */
  onSignOut?: () => void;
  ariaLabel: string;
  footer: ReactNode;
  className?: string;
}) {
  const pathname = usePathname();

  const renderItem = (item: NavItem) => {
    const active = isNavActive(pathname ?? "", item.href, { shellBase: basePath });
    const Icon = item.icon;
    const link = (
      <Link
        href={item.href}
        onClick={onNavigate}
        aria-current={active ? "page" : undefined}
        aria-label={collapsed ? (item.badge ? `${item.label}, ${item.badge}` : item.label) : undefined}
        className={cn(
          active ? b2cNavLinkActive : b2cNavLinkInactive,
          collapsed && "h-11 w-full justify-center !px-0 !py-0",
        )}
      >
        {Icon ? <Icon className="h-4 w-4 shrink-0" aria-hidden /> : null}
        {collapsed ? null : (
          <>
            <span className="min-w-0 flex-1 truncate">{item.label}</span>
            {item.badge ? (
              <span className="shrink-0 rounded-full bg-osce-navActive px-2 py-0.5 text-osce-caption font-semibold text-osce-ink-700">
                {item.badge}
              </span>
            ) : null}
          </>
        )}
      </Link>
    );

    return collapsed ? (
      <NavTooltip key={item.key} label={item.label}>
        {link}
      </NavTooltip>
    ) : (
      <Fragment key={item.key}>{link}</Fragment>
    );
  };

  const signOutButton = onSignOut ? (
    <button
      type="button"
      onClick={onSignOut}
      aria-label={collapsed ? "Sign out" : undefined}
      className={cn(
        b2cNavLinkInactive,
        "w-full",
        collapsed && "h-11 justify-center !px-0 !py-0",
      )}
    >
      <MdLogout className="h-4 w-4 shrink-0" aria-hidden />
      {collapsed ? null : <span>Sign out</span>}
    </button>
  ) : null;

  const hasGeneral =
    signOutButton !== null && groups.sections.some((group) => group.section === "general");

  return (
    <nav className={cn("min-h-0 flex-1 flex-col", className)} aria-label={ariaLabel}>
      <div className={cn(b2cScrollY, "min-h-0 flex-1", collapsed ? "py-3" : "pb-4")}>
        {collapsed ? (
          <div className="flex flex-col gap-1.5 px-1.5">
            {groups.ungrouped.map(renderItem)}
            {groups.sections.flatMap((group) => group.items).map(renderItem)}
            {hasGeneral ? <NavTooltip label="Sign out">{signOutButton}</NavTooltip> : null}
          </div>
        ) : (
          <div className="flex flex-col px-3">
            {groups.ungrouped.length > 0 ? (
              <div className="flex flex-col gap-px">{groups.ungrouped.map(renderItem)}</div>
            ) : null}
            {groups.sections.map((group) => (
              <div key={group.section}>
                <p className={b2cNavSectionLabel}>{group.label}</p>
                <div className="flex flex-col gap-px">
                  {group.items.map(renderItem)}
                  {group.section === "general" ? signOutButton : null}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      {footer}
    </nav>
  );
}
