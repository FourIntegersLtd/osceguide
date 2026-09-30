import {
  LuActivity,
  LuBuilding2,
  LuFlag,
  LuGauge,
  LuHandCoins,
  LuInbox,
  LuReceipt,
  LuScrollText,
  LuShieldCheck,
  LuUsers,
} from "react-icons/lu";
import type { NavContext, NavItem, SurfaceManifest } from "@/surfaces/contract";

/**
 * The OSCE Guide staff console.
 *
 * Not an arm anybody buys, and not a workspace: it lives at `/staff` rather
 * than under `/app/<workspace>` because nobody belongs to the platform the way
 * they belong to an organisation. It is deliberately the plainest skin so it
 * is never mistaken for a customer's screen in a screenshot.
 *
 * It is still declared here, because the shell, the navigation and the help
 * assistant all want the same treatment here as anywhere else.
 */
function nav({ href }: NavContext): NavItem[] {
  return [
    // Ungrouped on purpose: the landing screen sits above the section headings.
    { key: "overview", label: "Overview", href: href(""), icon: LuGauge },
    {
      key: "orgs",
      label: "Organisations",
      href: href("/organizations"),
      icon: LuBuilding2,
      section: "customers",
    },
    {
      key: "users",
      label: "Users",
      href: href("/users"),
      icon: LuUsers,
      section: "customers",
    },
    {
      key: "messages",
      label: "Messages",
      href: href("/messages"),
      icon: LuInbox,
      section: "customers",
    },
    {
      key: "billing",
      label: "Billing",
      href: href("/billing"),
      icon: LuReceipt,
      section: "revenue",
    },
    {
      key: "referralPayouts",
      label: "Referral payouts",
      href: href("/referral-payouts"),
      icon: LuHandCoins,
      section: "revenue",
    },
    {
      key: "stationFlags",
      label: "Station reports",
      href: href("/station-flags"),
      icon: LuFlag,
      section: "catalogue",
    },
    {
      key: "team",
      label: "Platform team",
      href: href("/team"),
      icon: LuShieldCheck,
      section: "operations",
    },
    {
      key: "audit",
      label: "Audit log",
      href: href("/audit"),
      icon: LuScrollText,
      section: "operations",
    },
    {
      key: "ops",
      label: "Machinery",
      href: href("/ops"),
      icon: LuActivity,
      section: "operations",
    },
  ];
}

export const platformSurface: SurfaceManifest = {
  id: "platform",
  label: "OSCE Guide staff",
  // Reached by permission, not by belonging to a workspace.
  workspaceKinds: [],
  nav,
  // Every `/staff/*` page is an explicit route file; this list is the
  // declaration the registry tests check nav destinations against.
  screenNames: [
    "dashboard",
    "organizations",
    "users",
    "team",
    "billing",
    "messages",
    "audit",
    "ops",
    "stationFlags",
    "referralPayouts",
  ],
};
