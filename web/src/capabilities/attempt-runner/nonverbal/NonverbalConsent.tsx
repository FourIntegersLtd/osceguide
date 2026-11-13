"use client";

import { useState } from "react";
import { PlatformError } from "@/foundation/platform-client";
import { ConfirmModal } from "@/foundation/ui";
import { setNonverbalConsent } from "./api";

const POINTS = [
  "Your video is analysed on this device. It is not recorded, not sent to us and not shown to the patient.",
  "Only measurements (numbers, once a second) are sent to OSCE Guide. They are deleted once your feedback is written.",
  "It describes what you did, not how you felt, and can be wrong in poor light or with an off-centre camera.",
  "It never affects your mark, and only you can see it.",
  "You can turn it off at any time. Turning it off in your account deletes this data.",
];

/**
 * The consent step for camera cues. Confirming asks the browser for the camera once (so the
 * prompt appears now, not mid-consultation), then records consent with the wording version shown.
 */
export function NonverbalConsent({ isOpen, version, onCancel, onGranted, onStale }: {
  isOpen: boolean;
  version: string;
  onCancel: () => void;
  onGranted: () => void;
  /** The wording changed since it was read: re-read so the new version and text show. */
  onStale: () => void;
}) {
  const [error, setError] = useState<string | null>(null);

  const confirm = async () => {
    setError(null);
    try {
      const probe = await navigator.mediaDevices.getUserMedia({ video: true });
      probe.getTracks().forEach((track) => track.stop());
    } catch {
      setError("Camera access is blocked. Allow it in your browser to get non-verbal cues.");
      return;
    }
    try {
      await setNonverbalConsent(true, version);
    } catch (caught) {
      if (caught instanceof PlatformError && caught.code === "nonverbal_consent_version_stale") {
        onStale();
        setError("The wording has been updated. Read it again and confirm.");
        return;
      }
      setError("We could not save your choice. Try again.");
      return;
    }
    onGranted();
  };

  return (
    <ConfirmModal
      isOpen={isOpen}
      title="Non-verbal feedback"
      confirmText="Turn on and allow camera"
      onCancel={() => {
        setError(null);
        onCancel();
      }}
      onConfirm={confirm}
      error={error}
      closeOnBack={false}
      message={
        <div className="space-y-3 text-left">
          <p>
            With your camera on, we measure where you are facing, when you nod and smile, and
            whether you are in view. You get live cues during the consultation and a short section
            in your feedback afterwards.
          </p>
          <ul className="list-disc space-y-1.5 pl-5">
            {POINTS.map((point) => <li key={point}>{point}</li>)}
          </ul>
        </div>
      }
    />
  );
}
