import type { Metadata } from "next";
import { Suspense } from "react";
import { NewOrganisation } from "@/domains/assess";
import { RequireAnonymous } from "@/foundation/session";

export const metadata: Metadata = { title: "Register your organisation" };

export default function Page() {
  return (
    <Suspense fallback={null}>
      <RequireAnonymous>
        <NewOrganisation />
      </RequireAnonymous>
    </Suspense>
  );
}
