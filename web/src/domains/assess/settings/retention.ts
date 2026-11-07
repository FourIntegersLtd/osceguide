/** The retention choices an administrator is offered, in days; `null` keeps everything. */
export const RETENTION_CHOICES: readonly { days: number | null; label: string }[] = [
  { days: 90, label: "90 days" },
  { days: 365, label: "1 year" },
  { days: null, label: "Keep until I delete them" },
];

/** The choice that matches what the organisation holds now, or "custom" for a value set outside this screen. */
export function retentionChoiceKey(days: number | null | undefined): string {
  const found = RETENTION_CHOICES.find((choice) => choice.days === (days ?? null));
  return found ? String(found.days) : "custom";
}
