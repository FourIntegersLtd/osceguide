import { headers } from "next/headers";
import { SITE_URL } from "@/app/metadata";

/**
 * One JSON-LD block. Carries the CSP nonce the middleware minted (`x-nonce`),
 * as Next's own scripts do, so it runs under an enforced `script-src` too. `<`
 * is escaped so no value can close the tag early.
 */
export async function JsonLd({ data }: { data: Record<string, unknown> }) {
  const nonce = (await headers()).get("x-nonce") ?? undefined;
  return (
    <script
      type="application/ld+json"
      nonce={nonce}
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }}
    />
  );
}

/** Organization and WebSite structured data, on every page. */
export function SiteJsonLd() {
  return (
    <JsonLd
      data={{
        "@context": "https://schema.org",
        "@graph": [
          {
            "@type": "Organization",
            "@id": `${SITE_URL}/#organization`,
            name: "OSCE Guide",
            url: SITE_URL,
            logo: `${SITE_URL}/og-image.png`,
            legalName: "Four Integers Ltd",
          },
          {
            "@type": "WebSite",
            "@id": `${SITE_URL}/#website`,
            name: "OSCE Guide",
            url: SITE_URL,
            inLanguage: "en-GB",
            publisher: { "@id": `${SITE_URL}/#organization` },
          },
        ],
      }}
    />
  );
}
