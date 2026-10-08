/** Whether an address plausibly belongs to the partner (bmj -> bmj.com, bmj.co.uk, mail.bmj.org). */
export function isPartnerAddress(email: string, partner: string): boolean {
  const host = email.trim().toLowerCase().split("@")[1] ?? "";
  return host.split(".").slice(0, -1).includes(partner.toLowerCase());
}
