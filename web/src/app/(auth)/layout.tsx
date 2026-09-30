import type { ReactNode } from "react";
import Link from "next/link";
import Logo from "@/foundation/ui/Logo";
import { authHeader } from "@/foundation/ui/authTheme";

/**
 * Signing in, and everything next to it.
 *
 * Its own group because these pages belong to no workspace: a person on them
 * has no arm yet, and wrapping them in a surface shell would show them a
 * navigation they cannot use.
 *
 * The header is the one thing every retiring auth page had and this port
 * dropped: a logo with a way back to the marketing site. Without it a sign-in
 * form has no brand on it and no exit — the only way off the page was the
 * browser's own back button.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-osce-canvas">
      <header className={authHeader}>
        <div className="mx-auto flex max-w-6xl items-center px-4 py-3 sm:px-6">
          <Link href="/" aria-label="OSCE Guide home">
            <Logo variant="light" interactive={false} />
          </Link>
        </div>
      </header>
      <div className="flex flex-1 flex-col px-4 py-8">{children}</div>
    </div>
  );
}
