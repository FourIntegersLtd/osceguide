"use client";

import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import ReactConfetti from "react-confetti";
import { BsStarFill } from "react-icons/bs";
import Modal from "@/foundation/ui/Modal";
import {
  ModalContent,
  ModalFooterActions,
  ModalHelper,
  ModalPrimaryButton,
  ModalTitle,
} from "@/foundation/ui/ModalContent";
import { b2cStatValue } from "@/foundation/ui/productTokens";

interface ConfettiProps {
  isActive: boolean;
  title?: string;
  message?: string;
  badgeCount?: number;
  /** When set, shows this number as the milestone count (no badge stars). */
  milestoneCount?: number;
  currentStreak?: number;
  onClose?: () => void;
}

const MAX_VISIBLE_BADGES = 8;

const Confetti: React.FC<ConfettiProps> = ({
  isActive,
  title,
  message,
  badgeCount = 0,
  milestoneCount,
  onClose,
}) => {
  const [windowSize, setWindowSize] = useState(() =>
    typeof window === "undefined"
      ? { width: 0, height: 0 }
      : { width: window.innerWidth, height: window.innerHeight },
  );
  const [mounted, setMounted] = useState(false);
  const [showOverlay, setShowOverlay] = useState(false);
  /** Bumped per celebration so each run gets a fresh ReactConfetti instance. */
  const [runId, setRunId] = useState(0);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!isActive) {
      setShowOverlay(false);
      return;
    }
    setShowOverlay(true);
    setRunId((id) => id + 1);
    const timer = setTimeout(() => {
      setShowOverlay(false);
      onCloseRef.current?.();
    }, 20000);
    return () => clearTimeout(timer);
  }, [isActive]);

  useEffect(() => {
    if (!isActive) return;
    const updateSize = () => {
      setWindowSize((size) =>
        size.width === window.innerWidth && size.height === window.innerHeight
          ? size
          : { width: window.innerWidth, height: window.innerHeight },
      );
    };
    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, [isActive]);

  const handleClose = () => {
    setShowOverlay(false);
    onCloseRef.current?.();
  };

  if (!isActive || !showOverlay) return null;

  const visibleBadges = Math.min(badgeCount, MAX_VISIBLE_BADGES);

  return (
    <>
      {mounted && windowSize.width > 0
        ? createPortal(
            <div className="pointer-events-none fixed inset-0 z-[110]">
              <ReactConfetti
                key={runId}
                canvasRef={canvasRef}
                width={windowSize.width}
                height={windowSize.height}
                numberOfPieces={280}
                recycle={false}
                gravity={0.45}
                tweenDuration={10000}
                colors={["#FFD700", "#4169E1", "#32CD32", "#FF8C00", "#8A2BE2"]}
              />
            </div>,
            document.body,
          )
        : null}

      <Modal
        onClose={handleClose}
        width="28rem"
        height="fit-content"
        hideCloseButton
      >
        <ModalContent className="space-y-4 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border-4 border-osce-accent/20 bg-osce-accent-subtle">
            <span className="text-osce-title" aria-hidden>
              🏆
            </span>
          </div>

          {title ? (
            <ModalTitle className="text-osce-body">{title}</ModalTitle>
          ) : null}

          {message ? (
            <ModalHelper className="mt-0 text-osce-body">{message}</ModalHelper>
          ) : null}

          {milestoneCount != null && milestoneCount > 0 ? (
            <div className="flex flex-col items-center py-1">
              <span className={b2cStatValue}>
                {milestoneCount}
              </span>
              <span className="mt-1 text-osce-body text-b2c-text-muted">
                total sessions completed
              </span>
            </div>
          ) : null}

          {badgeCount > 0 && milestoneCount == null ? (
            <div className="space-y-3">
              <p className="rounded-lg bg-osce-accent-muted px-3 py-2 text-osce-body font-medium text-osce-accent-hover">
                {badgeCount} milestone {badgeCount === 1 ? "badge" : "badges"}{" "}
                earned
              </p>
              <div className="flex flex-wrap justify-center gap-2">
                {Array.from({ length: visibleBadges }).map((_, index) => (
                  <div
                    key={index}
                    className="flex h-11 w-11 items-center justify-center rounded-lg bg-gradient-to-br from-osce-accent via-osce-accent to-osce-accent-hover"
                  >
                    <BsStarFill className="text-osce-body text-white/90" aria-hidden />
                  </div>
                ))}
              </div>
              {badgeCount > MAX_VISIBLE_BADGES ? (
                <p className="text-osce-caption text-b2c-text-muted">
                  +{badgeCount - MAX_VISIBLE_BADGES} more
                </p>
              ) : null}
            </div>
          ) : null}

          <ModalFooterActions className="justify-center sm:justify-end">
            <ModalPrimaryButton type="button" onClick={handleClose}>
              Continue
            </ModalPrimaryButton>
          </ModalFooterActions>
        </ModalContent>
      </Modal>
    </>
  );
};

export default Confetti;
