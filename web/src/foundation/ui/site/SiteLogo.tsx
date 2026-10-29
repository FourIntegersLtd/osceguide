import Link from "next/link";

/** The OSCE Guide mark and wordmark, linking home. Colours follow the site tokens. */
export function SiteLogo({ onDark = false }: { onDark?: boolean }) {
  return (
    <Link
      href="/"
      aria-label="OSCE Guide home"
      className={`inline-flex items-center gap-2 font-landing-heading text-lg font-bold ${onDark ? "text-white" : "text-site-ink"}`}
    >
      <svg width="30" height="25" viewBox="0 0 34 28" aria-hidden="true">
        <path d="M4 2h18l10 12-10 12H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z" className={onDark ? "fill-site-pale-strong" : "fill-site-brand"} />
        <path
          d="M19.5 10.2A5.6 5.6 0 1 0 20 16h-5"
          fill="none"
          className={onDark ? "stroke-site-navy" : "stroke-site-on-brand"}
          strokeWidth="2.6"
          strokeLinecap="round"
        />
      </svg>
      OSCE Guide
    </Link>
  );
}
