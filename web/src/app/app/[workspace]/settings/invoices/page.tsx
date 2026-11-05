/*
 * An organisation's invoices, reached from the Settings "Invoices" tab. Org admins only: the
 * page itself checks `manage_team`, as the api's invoice routes require an org admin.
 */

import type { Metadata } from "next";
import { Capability } from "@/app/app/[workspace]/capability";
import { InvoicesPage } from "@/domains/assess";

export const metadata: Metadata = { title: "Invoices" };

export default function Page() {
  return (
    <Capability id="account">
      <InvoicesPage />
    </Capability>
  );
}
