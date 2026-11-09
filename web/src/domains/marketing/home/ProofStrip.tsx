import { QuoteCard } from "@/domains/marketing/home/QuoteCard";
import { PROOF_QUOTES } from "@/domains/marketing/landingCopy";

/** Three passed-it quotes straight under the hero, before any explanation. */
export function ProofStrip() {
  return (
    <section aria-label="What doctors say" className="border-y border-site-line bg-site-pale px-4 py-12 sm:px-5">
      <div className="mx-auto grid max-w-[1280px] gap-8 sm:grid-cols-3">
        {PROOF_QUOTES.map((q) => (
          <QuoteCard key={q.name} q={q} />
        ))}
      </div>
    </section>
  );
}
