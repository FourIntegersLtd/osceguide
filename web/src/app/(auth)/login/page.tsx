import type { Metadata } from "next";
import { Suspense } from "react";
import { Login } from "@/capabilities/account";

export const metadata: Metadata = { title: "Sign in" };

export default function Page() {
  // These screens read the query string, which needs a boundary in the app
  // router. Nothing to show while it resolves: the form is the page.
  return (
    <Suspense fallback={null}>
      <Login />
    </Suspense>
  );
}
