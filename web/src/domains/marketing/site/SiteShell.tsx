import type { ReactNode } from "react";
import { SiteFooter } from "@/domains/marketing/site/SiteFooter";
import type { ExamKey } from "@/domains/marketing/landingExams";
import type { SiteLink } from "@/domains/marketing/site/siteLinks";
import { SiteNav } from "@/domains/marketing/site/SiteNav";

/** Nav, content and footer on the site tokens. `footer="card"` floats a white footer over the bottom of the closing band. */
export function SiteShell({ children, nav = "site", footer = "navy", exam, links }: { children: ReactNode; nav?: "landing" | "site"; footer?: "navy" | "card"; exam?: ExamKey; links?: readonly SiteLink[] }) {
  return (
    <div className="site-root min-h-screen font-landing-body antialiased">
      <a
        href="#site-main"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-site-brand focus:px-4 focus:py-2 focus:text-site-on-brand"
      >
        Skip to content
      </a>
      <SiteNav variant={nav} exam={exam} links={links} />
      <main id="site-main">{children}</main>
      <SiteFooter variant={footer} />
    </div>
  );
}
