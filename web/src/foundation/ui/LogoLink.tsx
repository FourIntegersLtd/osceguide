import Link from "next/link";
import Logo from "@/foundation/ui/Logo";

/**
 * The real OSCE Guide logo as a link home, for the public site and the auth
 * header. `onDark` is for the navy footer. Otherwise both skins render and
 * `siteTokens.css` shows the white-wordmark one in dark mode.
 */
export function LogoLink({ onDark = false }: { onDark?: boolean }) {
  return (
    <Link href="/" aria-label="OSCE Guide home" className="inline-flex min-h-11 items-center">
      {onDark ? (
        <Logo variant="dark" interactive={false} />
      ) : (
        <>
          <Logo variant="light" interactive={false} className="site-logo-light" />
          <Logo variant="dark" interactive={false} className="site-logo-dark" />
        </>
      )}
    </Link>
  );
}
