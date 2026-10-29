import { Eyebrow } from "@/foundation/ui";
import Link from "next/link";
import type { ReactNode } from "react";
import { SUPPORT_EMAIL } from "@/foundation/support";
import { SiteShell } from "@/domains/marketing/site/SiteShell";
import { COMPLIANCE_DOCS, complianceDates, type ComplianceDocKey } from "@/domains/marketing/legal/legalDocs";
import { LegalContents } from "@/domains/marketing/legal/LegalContents";

/**
 * The shared layout of the six compliance documents: hero with the document's
 * dates, a tab row across the documents, a sticky "On this page" and the
 * reading column. The children are the legal text and are rendered untouched;
 * only their typography is set here.
 */
export function LegalPage({ doc, title, children }: { doc: ComplianceDocKey; title: string; children: ReactNode }) {
  const { effective, updated } = complianceDates(doc);
  const dates = [effective && `Effective ${effective}`, updated && `Last updated ${updated}`].filter(Boolean).join(" · ");

  return (
    <SiteShell>
      <section className="border-b border-site-line bg-site-card">
        <div className="mx-auto max-w-[1200px] px-4 pb-0 pt-14 sm:px-6">
          <p><Eyebrow>Legal</Eyebrow></p>
          <h1 className="mt-3 font-landing-heading text-[32px] font-bold leading-tight text-site-ink sm:text-[44px]">{title}</h1>
          {dates && <p className="mt-3 text-sm text-site-muted">{dates}</p>}
          <nav aria-label="Legal documents" className="-mx-4 mt-8 overflow-x-auto px-4 sm:mx-0 sm:px-0">
            <ul className="flex gap-6 whitespace-nowrap">
              {COMPLIANCE_DOCS.map((d) => (
                <li key={d.key}>
                  <Link
                    href={d.href}
                    aria-current={d.key === doc ? "page" : undefined}
                    className={`block border-b-[3px] pb-3 text-sm font-medium transition-colors ${
                      d.key === doc ? "border-site-brand text-site-brand" : "border-transparent text-site-muted hover:text-site-ink"
                    }`}
                  >
                    {d.tabLabel}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        </div>
      </section>

      <div className="mx-auto grid max-w-[1200px] gap-8 px-4 py-12 sm:px-6 lg:grid-cols-[280px_minmax(0,1fr)] lg:gap-14">
        <aside className="lg:sticky lg:top-24 lg:self-start">
          <LegalContents />
          <div className="mt-6 rounded-xl border border-site-line bg-site-card p-4 text-sm text-site-body">
            <b className="block text-site-ink">Questions?</b>
            <a href={`mailto:${SUPPORT_EMAIL}`} className="mt-1 block break-all text-site-brand underline-offset-2 hover:underline">
              {SUPPORT_EMAIL}
            </a>
          </div>
        </aside>
        <article
          id="legal-body"
          className={[
            "min-w-0 max-w-[72ch] text-base leading-relaxed text-site-body",
            "[&_h2]:scroll-mt-24 [&_h2]:font-landing-heading [&_h2]:text-2xl [&_h2]:font-bold [&_h2]:text-site-ink",
            "[&_section]:border-b [&_section]:border-site-line [&_section]:pb-8",
            "[&_p]:text-site-body [&_li]:text-site-body [&_strong]:text-site-ink",
            "[&_a]:text-site-brand [&_a]:underline [&_a]:underline-offset-2",
            "[&_td]:text-site-body [&_th]:text-site-ink",
          ].join(" ")}
        >
          {children}
        </article>
      </div>
    </SiteShell>
  );
}
