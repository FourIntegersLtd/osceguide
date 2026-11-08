export type QuoteCardData = { text: string; highlight?: string; name: string; role: string };

/** A quote with its highlight in brand, then the doctor's name and role. */
export function QuoteCard({ q, className = "" }: { q: QuoteCardData; className?: string }) {
  const { highlight = "" } = q;
  const at = highlight ? q.text.indexOf(highlight) : -1;
  const [a, b, c] = at < 0 ? [q.text, "", ""] : [q.text.slice(0, at), highlight, q.text.slice(at + highlight.length)];
  return (
    <figure className={`flex h-full min-w-0 flex-col text-left ${className}`}>
      <blockquote className="flex-1 leading-relaxed text-site-body">
        &ldquo;{a}
        {b && <mark className="rounded bg-site-pale px-0.5 font-semibold text-site-brand">{b}</mark>}
        {c}&rdquo;
      </blockquote>
      <figcaption className="mt-3 text-sm">
        <b className="text-site-ink">{q.name}</b> <span className="text-site-muted">{q.role}</span>
      </figcaption>
    </figure>
  );
}
