import type { Metadata } from "next";
import { Suspense } from "react";
import { ChangePasswordRequired } from "@/capabilities/account";
import { RequireSession } from "@/foundation/session";

export const metadata: Metadata = { title: "Choose a new password" };

export default function Page() {
  // Reads `?next`, so it needs a boundary; the form is the whole page.
  return (
    <Suspense fallback={null}>
      <RequireSession allowMustChange>
        <ChangePasswordRequired />
      </RequireSession>
    </Suspense>
  );
}
