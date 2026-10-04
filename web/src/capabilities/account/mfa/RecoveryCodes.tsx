"use client";

import { useState } from "react";
import { HiOutlineArrowDownTray, HiOutlineClipboard } from "react-icons/hi2";
import { Button } from "@/foundation/ui";
import { recoveryCodesFile } from "@/capabilities/account/mfa/codes";

/**
 * Recovery codes, shown the one time the server ever sends them.
 *
 * `onDone` is withheld until the person says they have kept them: there is no
 * second chance to read these, and a lost phone without them is a support
 * ticket rather than a sign-in.
 */
export function RecoveryCodes({
  codes,
  doneLabel,
  onDone,
}: {
  codes: readonly string[];
  doneLabel: string;
  onDone: () => void;
}) {
  const [kept, setKept] = useState(false);
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(codes.join("\n"));
      setCopied(true);
    } catch {
      // Clipboard refused (permissions, an insecure origin). Download still works.
      setCopied(false);
    }
  };

  const download = () => {
    const url = URL.createObjectURL(
      new Blob([recoveryCodesFile(codes, new Date())], { type: "text/plain" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "osce-guide-recovery-codes.txt";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <p className="text-osce-body text-ink">
        Keep these somewhere safe. Each one signs you in once if you lose your authenticator.
        This is the only time we will show them.
      </p>
      <ul
        aria-label="Recovery codes"
        className="grid grid-cols-2 gap-2 rounded-osce-lg border border-border bg-canvas p-4 font-mono text-osce-data text-ink"
      >
        {codes.map((code) => (
          <li key={code}>{code}</li>
        ))}
      </ul>
      <div className="flex flex-wrap gap-2">
        <Button type="button" variant="secondary" size="sm" className="gap-1.5" onClick={() => copy()}>
          <HiOutlineClipboard className="h-4 w-4" aria-hidden />
          {copied ? "Copied" : "Copy"}
        </Button>
        <Button type="button" variant="secondary" size="sm" className="gap-1.5" onClick={download}>
          <HiOutlineArrowDownTray className="h-4 w-4" aria-hidden />
          Download
        </Button>
      </div>
      <label className="flex items-start gap-2 text-osce-body text-ink">
        <input
          type="checkbox"
          className="mt-1"
          checked={kept}
          onChange={(event) => setKept(event.target.checked)}
        />
        I have saved my recovery codes
      </label>
      <Button type="button" fullWidth disabled={!kept} onClick={onDone}>
        {doneLabel}
      </Button>
    </div>
  );
}
