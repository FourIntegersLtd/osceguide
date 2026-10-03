import type { Metadata } from "next";
import { Suspense } from "react";
import { ResetPassword } from "@/capabilities/account";

export const metadata: Metadata = { title: "Accept your invitation" };

export default function Page() {
  // An invitation's token is a password-reset token, so accepting one is
  // choosing a password: the same screen and the same route, worded for
  // somebody who has never signed in. The query string needs the boundary.
  return (
    <Suspense fallback={null}>
      <ResetPassword invitation />
    </Suspense>
  );
}
