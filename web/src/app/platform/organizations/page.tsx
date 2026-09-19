import type { Metadata } from "next";
import { Organizations } from "@/domains/platform";

export const metadata: Metadata = { title: "Organisations" };

export default function OrganizationsPage() {
  return <Organizations />;
}
