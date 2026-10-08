import { formatMoney, plural } from "@/foundation/format";

/** "£12.00 owed to 2 referrers", from the totals the server counted over the whole queue. */
export function owedHeadline(owed: { owed_pence: number; referrers: number }): string {
  if (owed.owed_pence === 0 && owed.referrers === 0) return "Nothing owed";
  return `${formatMoney(owed.owed_pence)} owed to ${plural(owed.referrers, "referrer")}`;
}
