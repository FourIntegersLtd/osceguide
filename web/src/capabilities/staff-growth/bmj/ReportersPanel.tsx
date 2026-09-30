"use client";

import { useState } from "react";
import { HiOutlineUserPlus } from "react-icons/hi2";
import {
  Alert,
  AsyncBoundary,
  Button,
  ConfirmModal,
  Input,
  Modal,
  ModalContent,
  ModalFooterActions,
  ModalLead,
  ModalPrimaryButton,
  ModalSecondaryButton,
  Panel,
  Row,
  RowList,
} from "@/foundation/ui";
import { errorMessage, useAsync, useToast } from "@/foundation/hooks";
import { partnerDisplayName } from "@/foundation/attribution/viewModel";
import {
  addPartnerReporter,
  listPartnerReporters,
  revokePartnerReporter,
} from "@/capabilities/staff-growth/api";

/** Whether an address plausibly belongs to the partner (bmj -> @bmj.com). */
export function isPartnerAddress(email: string, partner: string): boolean {
  return email.trim().toLowerCase().endsWith(`@${partner.toLowerCase()}.com`);
}

/** The people at the partner who may sign in to the partner dashboard: list, add, remove. */
export function ReportersPanel({ partner }: { partner: string }) {
  const name = partnerDisplayName(partner);
  const toast = useToast();
  const state = useAsync((signal) => listPartnerReporters(partner, signal), [partner]);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  const [removeBusy, setRemoveBusy] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);

  const remove = async () => {
    if (!removing) return;
    setRemoveBusy(true);
    setRemoveError(null);
    try {
      await revokePartnerReporter(partner, removing);
      toast.success(`Removed access for ${removing}`);
      setRemoving(null);
      state.reload();
    } catch (cause) {
      setRemoveError(errorMessage(cause));
    } finally {
      setRemoveBusy(false);
    }
  };

  return (
    <>
      <Panel
        title={`${name} viewers`}
        description={`People at ${name} who can sign in to see this dashboard.`}
        padding="none"
        actions={
          <Button type="button" onClick={() => setAdding(true)}>
            <HiOutlineUserPlus className="h-4 w-4" aria-hidden />
            Add viewer
          </Button>
        }
      >
        <AsyncBoundary
          state={state}
          isEmpty={(rows) => rows.every((row) => row.revoked_at)}
          empty={{
            title: "No viewers yet",
            description: `Add someone from ${name} to share this dashboard.`,
            bare: true,
          }}
          failure={(error, retry) => (
            <div className="p-5">
              <Alert tone="danger" title="We couldn't load viewers">
                <p>{error.message}</p>
                <div className="mt-3">
                  <Button variant="secondary" size="sm" onClick={retry}>
                    Try again
                  </Button>
                </div>
              </Alert>
            </div>
          )}
        >
          {(rows) => (
            <RowList flush>
              {rows
                .filter((row) => !row.revoked_at)
                .map((row) => (
                  <Row key={row.email}>
                    <div className="min-w-0">
                      <p className="truncate text-osce-data font-medium text-ink">{row.email}</p>
                      <p className="text-osce-meta text-ink-subtle">
                        Added {row.created_at.slice(0, 10)}
                      </p>
                    </div>
                    <Button variant="secondary" size="sm" onClick={() => setRemoving(row.email)}>
                      Remove
                    </Button>
                  </Row>
                ))}
            </RowList>
          )}
        </AsyncBoundary>
      </Panel>

      {adding ? (
        <AddViewerModal
          partner={partner}
          onClose={() => setAdding(false)}
          onAdded={() => {
            setAdding(false);
            toast.success("Viewer added");
            state.reload();
          }}
        />
      ) : null}

      <ConfirmModal
        isOpen={removing !== null}
        onCancel={() => {
          setRemoving(null);
          setRemoveError(null);
        }}
        onConfirm={() => void remove()}
        isLoading={removeBusy}
        error={removeError}
        tone="danger"
        title={`Remove access for ${removing ?? ""}?`}
        message="They will no longer be able to sign in to this dashboard."
        confirmText="Remove access"
      />
    </>
  );
}

function AddViewerModal({
  partner,
  onClose,
  onAdded,
}: {
  partner: string;
  onClose: () => void;
  onAdded: () => void;
}) {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const label = partner.toUpperCase();

  const submit = async () => {
    setError(null);
    const trimmed = email.trim();
    if (!trimmed) {
      setError("Please enter an email address.");
      return;
    }
    setBusy(true);
    try {
      await addPartnerReporter(partner, trimmed);
      onAdded();
    } catch (cause) {
      setError(errorMessage(cause));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal width="min(95vw, 480px)" height="fit-content" onClose={onClose} title={`Add ${label} viewer`}>
      <ModalContent>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          <ModalLead
            title={`Add ${label} viewer`}
            description="They will get an email with a password. They can only see this dashboard — not the exam product."
          />
          <div className="mt-5">
            <Input
              type="email"
              label="Work email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="name@bmj.com"
            />
          </div>
          {!error && email.includes("@") && !isPartnerAddress(email, partner) ? (
            <div className="mt-3">
              <Alert tone="warning">
                This isn&apos;t a {label} address. Double-check it before sending: whoever receives
                the email will be able to see this partner&apos;s commercial data.
              </Alert>
            </div>
          ) : null}
          {error ? (
            <div className="mt-3">
              <Alert tone="danger">{error}</Alert>
            </div>
          ) : null}
          <ModalFooterActions className="mt-6">
            <ModalSecondaryButton type="button" onClick={onClose} disabled={busy}>
              Cancel
            </ModalSecondaryButton>
            <ModalPrimaryButton type="submit" disabled={busy}>
              {busy ? "Sending…" : "Send invite"}
            </ModalPrimaryButton>
          </ModalFooterActions>
        </form>
      </ModalContent>
    </Modal>
  );
}
