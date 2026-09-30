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
  onSignOut: () => void;
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
        aria-label={collapsed ? item.label : undefined}
        className={cn(
          active ? b2cNavLinkActive : b2cNavLinkInactive,
          collapsed && "h-11 w-full justify-center !px-0 !py-0",
        )}
      >
        {Icon ? (
          <Icon
            className={cn(
              "h-5 w-5 shrink-0",
              active ? "text-osce-ink-900" : "text-b2c-text-muted",
            )}
            aria-hidden
          />
        ) : null}
        {collapsed ? null : (
          <span className="min-w-0 flex-1 truncate">{item.label}</span>
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

  const signOutButton = (
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
      <MdLogout className="h-5 w-5 shrink-0 text-b2c-text-muted" aria-hidden />
      {collapsed ? null : <span>Sign out</span>}
    </button>
  );

  const hasGeneral = groups.sections.some((group) => group.section === "general");

  return (
    <nav className={cn("min-h-0 flex-1 flex-col", className)} aria-label={ariaLabel}>
      <div className={cn(b2cScrollY, "min-h-0 flex-1", collapsed ? "py-3" : "py-4")}>
        {collapsed ? (
          <div className="flex flex-col gap-1.5 px-1.5">
            {groups.ungrouped.map(renderItem)}
            {groups.sections.flatMap((group) => group.items).map(renderItem)}
            {hasGeneral ? <NavTooltip label="Sign out">{signOutButton}</NavTooltip> : null}
          </div>
        ) : (
          <div className="flex flex-col px-2">
            {groups.ungrouped.length > 0 ? (
              <div className="mb-5 flex flex-col gap-0.5">{groups.ungrouped.map(renderItem)}</div>
            ) : null}
            {groups.sections.map((group) => (
              <div key={group.section} className="mb-5 last:mb-0">
                <p className={b2cNavSectionLabel}>{group.label}</p>
                <div className="flex flex-col gap-0.5">
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
