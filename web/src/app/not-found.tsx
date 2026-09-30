import Link from "next/link";

/**
 * No such page.
 *
 * Reached by a retired URL with no redirect, and by a workspace page an arm
 * does not answer — `/app/kings/mocks`, say, which is a consumer screen asked
 * of an institution. Both are genuinely "not here", so neither gets an
 * explanation that would only be right for one of them.
 */
export default function NotFound() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md text-center">
        <h1 className="text-lg font-semibold text-ink">Page not found</h1>
        <p className="mt-2 text-sm text-ink-muted">
          This page does not exist, or it belongs to a workspace you are not in.
        </p>
        <Link href="/app" className="mt-5 inline-block text-sm text-accent hover:underline">
          Go to your workspace
        </Link>
      </div>
    </main>
  );
}
