"use client";

import { useState } from "react";
import { HiOutlineVideoCamera } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { useToast } from "@/foundation/hooks";
import { setNonverbalConsent } from "@/capabilities/attempt-runner/nonverbal/api";
import { SettingsRow } from "@/capabilities/account/settings/SettingsKit";

/**
 * Withdraw camera consent and delete what was stored. The api has no consent read, so the row
 * claims no state: the button is safe to press at any time and says what it does.
 */
export function NonverbalPreferenceRow() {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const withdraw = async () => {
    setBusy(true);
    try {
      await setNonverbalConsent(false);
      toast.success("Non-verbal feedback is off and your stored data has been deleted");
    } catch {
      toast.error("Your change was not saved. Try again");
    } finally {
      setBusy(false);
    }
  };
  return (
    <SettingsRow
      icon={HiOutlineVideoCamera}
      title="Non-verbal feedback"
      meta="Optional camera cues in consultations. Your video stays on your device. You are asked again before the camera is used"
      trailing={<Button variant="secondary" size="sm" isLoading={busy} onClick={() => void withdraw()}>Turn off non-verbal feedback and delete its data</Button>}
    />
  );
}
