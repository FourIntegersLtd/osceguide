"use client";

import { useState } from "react";
import { Alert, Button, Input, Modal, Textarea } from "@/foundation/ui";
import { errorMessage, useToast } from "@/foundation/hooks";
import { sendUserNote } from "@/domains/platform/api";

/** A note to one person's inbox in the app. No email is sent. */
export function SendMessageModal({
  userId,
  onClose,
  onSent,
}: {
  userId: string;
  onClose: () => void;
  onSent: () => void;
}) {
  const toast = useToast();
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await sendUserNote(userId, { subject: subject.trim(), body: body.trim() });
      toast.success("Message sent");
      onSent();
      onClose();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal onClose={onClose} title="Send message" width="min(32rem, 96vw)">
      <form onSubmit={submit} className="flex flex-col gap-3 p-4 lg:p-6">
        {error ? <Alert tone="danger">{error}</Alert> : null}
        <Input label="Subject" required value={subject} maxLength={200} disabled={busy} onChange={(event) => setSubject(event.target.value)} />
        <Textarea
          label="Message"
          required
          value={body}
          maxLength={5000}
          disabled={busy}
          hint="Lands in their inbox in the app. We don't send email yet."
          onChange={(event) => setBody(event.target.value)}
        />
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" disabled={busy} onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" isLoading={busy} disabled={!subject.trim() || !body.trim()}>
            Send
          </Button>
        </div>
      </form>
    </Modal>
  );
}
