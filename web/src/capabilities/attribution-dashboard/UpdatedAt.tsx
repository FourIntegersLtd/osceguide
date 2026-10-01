/** "Updated 14:05", in the reader's own clock, the way the dashboard has always said it. */
export function UpdatedAt({ at }: { at: Date | null }) {
  if (!at) return null;
  return (
    <p className="text-right text-osce-caption text-ink-subtle">
      Updated {at.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })}
    </p>
  );
}
