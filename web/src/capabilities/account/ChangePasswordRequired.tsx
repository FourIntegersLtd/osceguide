"use client";

import { useRouter, useSearchParams } from "next/navigation";
import AuthShell from "@/capabilities/account/AuthShell";
import ChangePassword from "@/capabilities/account/settings/ChangePassword";
import { FORCED_PASSWORD_COPY } from "@/capabilities/account/support/signInCopy";
import { sanitizeReturnTo } from "@/foundation/session/returnTo";
import { useSession } from "@/foundation/session";

/**
 * The password change a person did not choose to make.
 *
 * An invitation creates an account with a link that sets a first password, and
 * the backend flags the account `must_change_password` until it has one of
 * theirs. `RequireSession` sends anyone carrying that flag here, so this is the
 * only screen a flagged account can reach — which is why it belongs to the
 * `(auth)` group rather than to Settings, where the same form sits as an option.
 *
 * The card itself is Settings' `ChangePassword`, unchanged: one implementation
 * of the form, one endpoint, and the difference between the two is only whether
 * a person arrived by choice or by requirement.
 */
export function ChangePasswordRequired() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { refresh } = useSession();

  const next = sanitizeReturnTo(searchParams.get("next"));

  return (
    <AuthShell
      title="Choose a new password"
      subtitle="You signed in with a temporary password. Choose your own before you carry on."
      variant="card"
      compact
    >
      <ChangePassword
        copy={FORCED_PASSWORD_COPY}
        onChanged={async () => {
          /*
           * The flag lives on `/me`, so the guard only stands down once the
           * session has been re-read — replacing first would land on a page that
           * immediately bounces back here.
           */
          await refresh();
          router.replace(next ?? "/app");
        }}
      />
    </AuthShell>
  );
}
