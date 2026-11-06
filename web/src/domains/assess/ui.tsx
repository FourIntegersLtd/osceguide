import { boardAlert, boardBtn, boardCardClipped, boardInput, boardLabel, boardChip, type AlertTone, type BoardChipTone } from "@/foundation/ui/boardKit";
import { useId, type ReactNode } from "react";
import { b2bTokens as t, cn, Modal } from "@/foundation/ui";
import { generateTemporaryPassword, MIN_LENGTH, temporaryPasswordIssue } from "@/foundation/session/temporaryPassword";

/**
 * The pieces of the People board (docs/institution-overhaul/boards/People.dc.html) that every
 * People panel, dialog and the Add people sheet repeat: buttons, chips, alerts, cards, rows and
 * form controls at the board's own sizes. Colours and type come from the assess tokens in
 * foundation/ui; nothing here is a new token.
 */

const FLAT_LEADING = "!leading-[normal]";

export function Chip({ tone = "neutral", children }: { tone?: BoardChipTone; children: ReactNode }) {
  return <span className={boardChip(tone)}>{children}</span>;
}

/** The board's `.al`. */
export function Note({ tone, children, role }: { tone: AlertTone; children: ReactNode; role?: "alert" | "status" }) {
  return (
    <div role={role} className={boardAlert(tone)}>
      {children}
    </div>
  );
}

/** The board's `.card`. */
export const card = boardCardClipped;
/** The board's `.row`: a line inside a card. */
export const row = "flex flex-wrap items-center gap-4 border-t border-osce-border-light px-5 py-4 text-assess-label text-osce-ink-900";
/** The board's `.th`. */
export const th = "flex flex-wrap gap-4 bg-osce-surface-inset px-5 py-2.5 text-assess-eyebrow uppercase text-osce-ink-500";
/** The board's `h2` in a card. */
export const h2 = `m-0 text-osce-body font-semibold ${FLAT_LEADING} text-osce-ink-900`;
/** The board's `.hint`. */
export const hint = cn(t.assessMeta, "mt-1.5");
/** The board's `.fields`: label and control pairs side by side. */
export const fields = "flex flex-wrap gap-4 [&>div]:flex-[1_1_200px]";
/** The board's `.acts`. */
export const acts = "flex flex-wrap items-center gap-2.5";

/** The board's `details.fold`, open: a summary line and a body, under a hairline. */
export function Fold({ title, children }: { title: string; children: ReactNode }) {
  return (
    <details className="border-t border-osce-border-light" open>
      <summary className="min-h-6 cursor-pointer px-5 py-3.5 text-assess-label font-medium">{title}</summary>
      <div className="flex flex-col gap-1 px-5 pb-4 text-assess-label leading-[1.6] text-osce-ink-700">{children}</div>
    </details>
  );
}

/**
 * The board's `.ov` and `.dlg`: a scrim and one 520px sheet with a title, a body, an inline failure
 * and Cancel plus a commit. The one dialog shape for the institution screens.
 */
export function PeopleDialog({
  open,
  title,
  lead,
  error,
  busy = false,
  commitLabel,
  busyLabel,
  commitDisabled = false,
  tone = "commit",
  onClose,
  onCommit,
  children,
}: {
  open: boolean;
  title: string;
  lead?: ReactNode;
  error?: string | null;
  busy?: boolean;
  /** Omit all three to show a read-only dialog with a single Close button (the board's "Result preview"). */
  commitLabel?: string;
  busyLabel?: string;
  commitDisabled?: boolean;
  tone?: "commit" | "danger";
  onClose: () => void;
  onCommit?: () => void;
  children?: ReactNode;
}) {
  const titleId = useId();
  if (!open) return null;
  // Escape and the backdrop are ignored while saving. Back is not: a Back the dialog ignored would still consume
  // its history entry, so a failed save would leave the next Back leaving the page. History is off while busy
  // (Back then behaves as on any page) and the marker is pushed again when the save ends.
  const close = () => {
    if (!busy) onClose();
  };
  return (
    <Modal onClose={close} closeOnBack={!busy} labelledBy={titleId} hideCloseButton width="35.5rem" panelClassName="max-w-[35.5rem]" bodyClassName="p-6">
      <div className="flex flex-col gap-3.5">
        <h2 id={titleId} className={`m-0 text-assess-desc font-semibold ${FLAT_LEADING} text-osce-ink-900`}>{title}</h2>
        {lead ? <p className="m-0 text-assess-label leading-[1.5] text-osce-ink-500">{lead}</p> : null}
        {children}
        {error ? <Note tone="bad" role="alert">{error}</Note> : null}
        <div className={cn(acts, "justify-end")}>
          <button type="button" className={boardBtn()} onClick={onClose} disabled={busy}>
            {onCommit ? "Cancel" : "Close"}
          </button>
          {onCommit ? (
            <button type="button" className={boardBtn(tone === "danger" ? "danger" : "primary")} onClick={onCommit} disabled={busy || commitDisabled}>
              {busy ? busyLabel : commitLabel}
            </button>
          ) : null}
        </div>
      </div>
    </Modal>
  );
}

/**
 * The board's temporary-password block: a check row, then the password and Generate side by side with one
 * hint below. Takes `useTemporaryPassword().field`. It stays beside `foundation/ui/TemporaryPasswordField`
 * (still used by the platform seat form) because the board changes the markup, not the rule: the strength
 * rule, Generate and the copy come from `foundation/session/temporaryPassword`, so only the layout is repeated.
 */
export function PasswordFields({
  enabled,
  onEnabledChange,
  value,
  onChange,
  disabled,
  id,
}: {
  enabled: boolean;
  onEnabledChange: (enabled: boolean) => void;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  id: string;
}) {
  const issue = value ? temporaryPasswordIssue(value) : null;
  return (
    <>
      <label className="m-0 flex min-h-8 cursor-pointer items-start gap-2.5 text-assess-label font-normal">
        <input type="checkbox" checked={enabled} disabled={disabled} onChange={(event) => onEnabledChange(event.target.checked)} className="mt-0.5 h-4 w-4" />
        Set a temporary password instead of emailing a link
      </label>
      {enabled ? (
        <div>
          <label htmlFor={id} className={boardLabel}>Temporary password</label>
          <div className="flex gap-2">
            <input id={id} type="text" required autoComplete="off" value={value} disabled={disabled} onChange={(event) => onChange(event.target.value)} className={boardInput} />
            <button type="button" className={boardBtn()} disabled={disabled} onClick={() => onChange(generateTemporaryPassword())}>
              Generate
            </button>
          </div>
          <div className={hint}>
            At least {MIN_LENGTH} characters, mixing letters with numbers, punctuation or capitals. Only used if they have no account yet; they must change it when they first sign in.
          </div>
          {issue ? <div className={cn(hint, "text-osce-danger-text")} role="alert">{issue}</div> : null}
        </div>
      ) : null}
    </>
  );
}
