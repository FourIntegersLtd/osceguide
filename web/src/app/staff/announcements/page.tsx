import type { Metadata } from "next";
import { Announcements } from "@/domains/platform";

export const metadata: Metadata = { title: "Announcements" };

export default function Page() {
  return <Announcements />;
}
