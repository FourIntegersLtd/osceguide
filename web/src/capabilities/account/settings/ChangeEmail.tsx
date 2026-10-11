"use client";

import { useState } from "react";
import { HiOutlineEnvelope } from "react-icons/hi2";
import { requestEmailChange } from "@/foundation/platform-client";
import { useSession } from "@/foundation/session";
import {
  ModalContent,
  ModalField,
  ModalFooterActions,
  ModalLead,
  ModalPrimaryButton,
  ModalSection,
} from "@/foundation/ui";
import Alert from "@/foundation/forms/Alert";
import { errorMessage, useToast } from "@/foundation/hooks";

const inputClassName =
  "w-full rounded-xl border border-osce-border bg-white px-3 py-2.5 text-osce-body text-ink outline-none transition focus:border-osce-accent-subtle focus:ring-2 focus:ring-osce-accent-muted";

/**
 * Change the address you sign in with. The server mails a link to the new
 * address and moves nothing until it is used, so the answer here is always
 * "check your inbox" -- it never says whether the address is already taken.
 */
export default function ChangeEmail() {
  const current = useSession().session?.user.email ?? "";
  const [newEmail, setNewEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const toast = useToast();
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await requestEmailChange(newEmail.trim(), password);
      toast.success(`We've sent a link to ${newEmail.trim()}`, "Your address changes when you use it.");
      setPassword("");
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <ModalContent>
      <ModalLead
        title="Update email"
        description={current ? `You sign in with ${current}.` : "Choose the address you sign in with."}
        icon={<HiOutlineEnvelope className="h-5 w-5" />}
      />
      {error ? <Alert message={error} type="error" /> : null}
      <form onSubmit={submit} className="space-y-7">
        <ModalSection title="New address">
          <div className="space-y-4">
            <ModalField label="New email" htmlFor="newEmail">
              <input id="newEmail" type="email" autoComplete="email" required value={newEmail} onChange={(e) => setNewEmail(e.target.value)} className={inputClassName} />
            </ModalField>
            <ModalField label="Current password" htmlFor="emailChangePassword">
              <input id="emailChangePassword" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} className={inputClassName} />
            </ModalField>
          </div>
        </ModalSection>
        <ModalFooterActions>
          <ModalPrimaryButton type="submit" disabled={busy}>
            {busy ? "Sending..." : "Send confirmation link"}
          </ModalPrimaryButton>
        </ModalFooterActions>
      </form>
    </ModalContent>
  );
}
