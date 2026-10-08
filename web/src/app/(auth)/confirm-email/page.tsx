import type { Metadata } from "next";
import { Suspense } from "react";
import { ConfirmEmail } from "@/capabilities/account";

export const metadata: Metadata = { title: "Confirm your new email" };

export default function Page() {
  return (
    <Suspense fallback={null}>
      <ConfirmEmail />
    </Suspense>
  );
}
