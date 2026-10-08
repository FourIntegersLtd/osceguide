import { formatMoney, plural } from "@/foundation/format";

type Payout = { earned_pence: number; referrer_email: string };

/** "£12.00 owed to 2 referrers", summed from the unpaid rows. */
export function owedHeadline(unpaid: Payout[]): string {
  if (unpaid.length === 0) return "Nothing owed";
  const total = unpaid.reduce((sum, row) => sum + row.earned_pence, 0);
  const referrers = new Set(unpaid.map((row) => row.referrer_email)).size;
  return `${formatMoney(total)} owed to ${plural(referrers, "referrer")}`;
}
