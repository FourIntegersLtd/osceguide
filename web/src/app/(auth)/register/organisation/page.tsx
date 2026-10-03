import type { Metadata } from "next";
import { NewOrganisation } from "@/domains/assess";
import { RequireAnonymous } from "@/foundation/session";

export const metadata: Metadata = { title: "Set up your organisation" };

export default function Page() {
  return (
    <RequireAnonymous>
      <NewOrganisation />
    </RequireAnonymous>
  );
}
