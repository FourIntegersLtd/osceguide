import { LuActivity, LuBuilding2, LuFlag, LuGauge, LuHandCoins, LuInbox, LuReceipt, LuScrollText, LuShieldCheck, LuUsers } from "react-icons/lu";
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
    { key: "overview", label: "Overview", href: href(""), icon: LuGauge, section: "console" },
    {
      key: "orgs",
      label: "Organisations",
      href: href("/organizations"),
      icon: LuBuilding2,
      section: "console",
    },
    { key: "users", label: "Users", href: href("/users"), icon: LuUsers, section: "console" },
    {
      key: "team",
      label: "Platform team",
      href: href("/team"),
      icon: LuShieldCheck,
      section: "console",
    },
    { key: "billing", label: "Billing", href: href("/billing"), icon: LuReceipt, section: "console" },
    { key: "messages", label: "Messages", href: href("/messages"), icon: LuInbox, section: "console" },
    { key: "audit", label: "Audit log", href: href("/audit"), icon: LuScrollText, section: "console" },
    {
      key: "stationFlags",
      label: "Station reports",
      href: href("/station-flags"),
      icon: LuFlag,
      section: "content",
    },
    {
      key: "referralPayouts",
      label: "Referral payouts",
      href: href("/referral-payouts"),
      icon: LuHandCoins,
      section: "console",
    },
    { key: "ops", label: "Machinery", href: href("/ops"), icon: LuActivity, section: "console" },
  ];
}

export const platformSurface: SurfaceManifest = {
  id: "platform",
  label: "OSCE Guide staff",
  // Reached by permission, not by belonging to a workspace.
  workspaceKinds: [],
  nav,
  screenNames: [
    "dashboard",
    "organizations",
    "users",
    "team",
    "billing",
    "audit",
    "ops",
    "stationFlags",
    "referralPayouts",
  ],
};
