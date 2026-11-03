"use client";

import React, { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { IoMdCloseCircle } from "react-icons/io";
import { cn } from "@/foundation/ui/cn";
import {
  isFitContentHeight,
  lockAppScroll,
  resolveModalWidth,
} from "@/foundation/ui/modalDom";
import { useFocusTrap } from "@/foundation/hooks/useFocusTrap";
import { useModalHistory } from "@/foundation/hooks/useModalHistory";

interface ModalPropType {
  onClose?: () => void;
  children: React.ReactNode;
  height?: string;
  width?: string | { mobile: string; desktop: string };
  /** Hide the close (X) control even when onClose is set. */
  hideCloseButton?: boolean;
  /** Accessible name. Rendered visually hidden unless `labelledBy` points at visible text. */
  title?: string;
  labelledBy?: string;
  describedBy?: string;
  initialFocusRef?: React.RefObject<HTMLElement | null>;
  /** Escape closes (default true when onClose is set). */
  closeOnEscape?: boolean;
  /** Clicking the backdrop closes (default true when onClose is set). */
  closeOnBackdrop?: boolean;
  /** Browser Back closes instead of leaving the page (default true when onClose is set). */
  closeOnBack?: boolean;
  className?: string;
  panelClassName?: string;
  closeBarClassName?: string;
  bodyClassName?: string;
}

/**
 * Portaled overlay. z-[100] beats mobile nav (20), drawer (50), and help FAB (50).
 * Mobile: bottom sheet. Desktop: centered card.
 */
export const b2cModalOverlayRoot =
  "fixed inset-0 z-[100] flex items-end justify-center md:items-center";

export const b2cModalOverlayBackdrop = "osce-modal-scrim absolute inset-0";

/** Bottom sheet on mobile; centered card on md+. */
export const b2cModalPanel =
  "relative z-[100] mx-2 flex w-full max-h-[90dvh] flex-col overflow-hidden rounded-t-osce-2xl border border-b2c-border bg-osce-surface shadow-[0_24px_64px_rgba(16,24,40,0.18)] md:mx-auto md:max-h-[min(90dvh,calc(100dvh-2rem))] md:rounded-osce-2xl focus:outline-none";

export const b2cModalPanelBody =
  "min-h-0 min-w-0 flex-1 overflow-x-hidden overflow-y-auto overscroll-contain p-4 pb-[max(1rem,env(safe-area-inset-bottom,0px))] [-webkit-overflow-scrolling:touch] sm:p-6";

export const b2cModalCloseBar =
  "flex shrink-0 justify-end px-3 pt-3 md:px-4";

const Modal = ({
  onClose,
  children,
  height,
  width,
  hideCloseButton = false,
  title,
  labelledBy,
  describedBy,
  initialFocusRef,
  closeOnEscape = true,
  closeOnBackdrop = true,
  closeOnBack = true,
  className = "",
  panelClassName = "",
  closeBarClassName = "",
  bodyClassName = "",
}: ModalPropType) => {
  const [mounted, setMounted] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const generatedTitleId = useId();

  useEffect(() => {
    // Portals need a DOM target, so render nothing until after hydration.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  useEffect(() => lockAppScroll(), []);

  useFocusTrap(panelRef, {
    enabled: mounted,
    initialFocusRef,
    onEscape: closeOnEscape && onClose ? onClose : undefined,
  });
  useModalHistory(Boolean(onClose) && closeOnBack, onClose);

  const resolvedWidth = resolveModalWidth(width);
  const fitContent = isFitContentHeight(height);
  const showClose = Boolean(onClose) && !hideCloseButton;
  const titleId = labelledBy ?? (title ? generatedTitleId : undefined);

  if (!mounted) return null;

  return createPortal(
    <div className={cn(b2cModalOverlayRoot, className)}>
      <div
        className={b2cModalOverlayBackdrop}
        aria-hidden="true"
        onClick={closeOnBackdrop ? onClose : undefined}
      />
      {/* Stops a click inside reaching whatever rendered the modal (portal
          events bubble through the React tree); not an action. */}
      {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={describedBy}
        className={cn(
          b2cModalPanel,
          "w-[min(100%,calc(100vw-1rem))] md:w-[var(--modal-width)] md:max-w-[min(var(--modal-width),calc(100vw-2rem))]",
          panelClassName,
        )}
        style={
          {
            ["--modal-width" as string]: resolvedWidth,
            height: fitContent ? "auto" : height,
            maxHeight: "90dvh",
          } as React.CSSProperties
        }
        onClick={(e) => e.stopPropagation()}
      >
        {title && !labelledBy ? (
          <h2 id={generatedTitleId} className="sr-only">
            {title}
          </h2>
        ) : null}
        {showClose ? (
          <div className={cn(b2cModalCloseBar, closeBarClassName)}>
            <button
              onClick={onClose}
              className="-m-1 flex h-11 w-11 items-center justify-center text-b2c-text-muted transition-colors duration-200 hover:text-osce-ink-900 md:m-0 md:h-auto md:w-auto"
              aria-label="Close dialog"
              type="button"
            >
              {/* Larger on a phone (44px tap target, 36px glyph); the desktop size is unchanged. */}
              <IoMdCloseCircle className="text-4xl md:text-osce-title" aria-hidden />
            </button>
          </div>
        ) : null}
        {/* The close bar already holds the top edge; full body padding under it left a blank band. */}
        <div className={cn(b2cModalPanelBody, showClose && "pt-2 sm:pt-2", bodyClassName)}>{children}</div>
      </div>
    </div>,
    document.body,
  );
};

export default Modal;
