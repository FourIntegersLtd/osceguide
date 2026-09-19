import type { Metadata } from "next";
import { Users } from "@/domains/platform";

export const metadata: Metadata = { title: "Users" };

export default function UsersPage() {
  return <Users />;
}
