import type { ReactNode } from "react";

/**
 * Signing in, and everything next to it.
 *
 * Its own group because these pages belong to no workspace: a person on them
 * has no arm yet, and wrapping them in a surface shell would show them a
 * navigation they cannot use.
 */
export default function AuthLayout({ children }: { children: ReactNode }) {
  return <div className="flex min-h-screen flex-col bg-osce-canvas px-4 py-8">{children}</div>;
}
