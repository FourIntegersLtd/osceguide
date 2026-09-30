"use client";

import {
  useEffect,
  useId,
  useRef,
  useCallback,
  type ReactNode,
  type KeyboardEvent,
} from "react";
import { createPortal } from "react-dom";
import { HiOutlineXMark } from "react-icons/hi2";

/** Preset max-widths; all use full width up to the cap on small screens. */
const sizeClasses = {
  sm: "max-w-sm",
  md: "max-w-lg",
  lg: "max-w-2xl",
  xl: "max-w-4xl",
  xxl: "max-w-6xl",
  /** ~1100px cap. station/template editors, library browser */
  wide: "max-w-[min(1100px,96vw)]",
  /** Team members "view all" Tables */
  members: "max-w-[min(960px,96vw)]",
  spreadsheet: "max-w-[min(720px,96vw)]",
  picker: "max-w-[min(560px,96vw)]",
  station: "max-w-[min(900px,92vw)]",
  /** Near-fullscreen. template structure builder */
  fullscreen: "max-w-[min(1400px,98vw)] max-h-[96vh]",
} as const;

function ModalBody({ children }: { children: ReactNode }) {
  return (
    <div className="bg-osce-surface px-4 py-4 text-osce-body text-ink-muted sm:px-6">
      {children}
    </div>
  );
}

function ModalFooter({ children }: { children: ReactNode }) {
  return (
    <div className="flex flex-col-reverse gap-2 border-t border-osce-border bg-osce-surface px-4 py-4 sm:flex-row sm:items-center sm:justify-end sm:gap-3 sm:px-6 [&>button]:w-full sm:[&>button]:w-auto">
      {children}
    </div>
  );
}

const FOCUSABLE =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

function getFocusable(el: HTMLElement): HTMLElement[] {
  return Array.from(el.querySelectorAll<HTMLElement>(FOCUSABLE));
}

type B2BModalChrome = "titlebar" | "plain";

type B2BModalProps = {
  open: boolean;
  onClose: () => void;
  /** Visible title in the modal header (`titlebar` And `plain`). */
  title: string;
  size?: keyof typeof sizeClasses;
  /**
   * `titlebar`. Default B2B header + optional Body/Footer compound children.
   * `plain`. Opaque header + scrollable body (large editors, library browsers).
   */
  chrome?: B2BModalChrome;
  /** Extra classes on the `<dialog>` (e.g. `max-h-[90vh]`). */
  className?: string;
  /** When `chrome` Is `plain`, classes for the inner scroll wrapper. */
  plainContentClassName?: string;
  /** Optional controls rendered beside the title when `chrome` Is `plain`. */
  headerExtra?: ReactNode;
  /** Suppress the default close button in the header. */
  hideCloseButton?: boolean;
  children: ReactNode;
};

export function B2BModal({
  open,
  onClose,
  title,
  size = "md",
  chrome = "titlebar",
  className = "",
  plainContentClassName = "min-h-0 flex-1 overflow-y-auto bg-osce-surface px-4 py-4 sm:px-6",
  headerExtra,
  hideCloseButton = false,
  children,
}: B2BModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  // Mount/unmount with `open`; native dialog top layer + body scroll lock
  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (!dialog.open) dialog.showModal();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      if (dialog.open) dialog.close();
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  // Handle Escape via the native cancel event → call onClose
  const handleCancel = useCallback(
    (e: Event) => {
      e.preventDefault();
      onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (!open) return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    dialog.addEventListener("cancel", handleCancel);
    return () => dialog.removeEventListener("cancel", handleCancel);
  }, [handleCancel, open]);

  // Focus trap
  const handleKeyDown = (e: KeyboardEvent<HTMLDialogElement>) => {
    if (e.key !== "Tab") return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    const focusable = getFocusable(dialog);
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (!first || !last) return;
    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  };

  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
    if (e.target === dialogRef.current) onClose();
  };

  if (typeof document === "undefined" || !open) return null;

  const widthClass = sizeClasses[size];
  const dialogA11y = { "aria-labelledby": titleId };
  const closeButtonClass =
    "inline-flex h-8 w-8 items-center justify-center rounded text-ink-muted hover:bg-osce-canvas hover:text-ink-muted focus:outline-none focus:ring-2 focus:ring-osce-accent/25";

  function renderCloseButton() {
    return (
      <button
        type="button"
        onClick={onClose}
        aria-label="Close dialog"
        className={closeButtonClass}
      >
        <HiOutlineXMark className="h-5 w-5" aria-hidden="true" />
      </button>
    );
  }

  return createPortal(
    // A click on the backdrop closes, as Escape does in `handleKeyDown`.
    // eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions
    <dialog
      ref={dialogRef}
      aria-modal="true"
      {...dialogA11y}
      onKeyDown={handleKeyDown}
      onClick={handleBackdropClick}
      className={[
        "b2b-app b2b-portal b2b-modal",
        "m-auto w-full rounded-osce-lg border border-osce-border bg-osce-surface p-0",
        widthClass,
        chrome === "plain" ? "max-h-[min(90vh,900px)] overflow-hidden" : "",
        className,
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {chrome === "titlebar" ? (
        <>
          <div className="flex items-start justify-between gap-3 border-b border-osce-border bg-osce-surface px-4 py-4 sm:items-center sm:px-6">
            <h2
              id={titleId}
              className="text-osce-subheading font-semibold text-ink"
            >
              {title}
            </h2>
            {!hideCloseButton ? renderCloseButton() : null}
          </div>
          {children}
        </>
      ) : (
        <>
          <div className="flex shrink-0 items-start gap-3 border-b border-osce-border bg-osce-surface px-4 py-4 sm:px-6">
            <div className="flex min-w-0 flex-1 flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <h2
                id={titleId}
                className="text-osce-subheading font-semibold text-ink"
              >
                {title}
              </h2>
              {headerExtra ? (
                <div className="shrink-0">{headerExtra}</div>
              ) : null}
            </div>
            {!hideCloseButton ? renderCloseButton() : null}
          </div>
          <div className={plainContentClassName}>{children}</div>
        </>
      )}
    </dialog>,
    document.body,
  );
}

B2BModal.Body = ModalBody;
B2BModal.Footer = ModalFooter;
