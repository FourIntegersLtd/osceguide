"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import type { IconType } from "react-icons";
import {
  HiOutlineCheckCircle,
  HiOutlineClock,
  HiOutlineExclamationTriangle,
  HiOutlineMicrophone,
  HiOutlineSpeakerWave,
} from "react-icons/hi2";
import { cn } from "@/foundation/ui/cn";
import { b2cBodyTextMuted, b2cGroupedRowTitle } from "@/foundation/ui/productTokens";

/**
 * Every LiveKit surface shows a bar visualiser that has nothing to visualise
 * until a room exists, leaving a flat grey stub above a large empty panel.
 * These pieces fill that space with who the user is about to speak to and
 * whether their setup is ready, and are swapped out once audio starts.
 */

export type LivekitIdleAvatar =
  | { kind: "image"; src: string; alt: string }
  | { kind: "monogram"; initials: string }
  /** For surfaces with no named subject to show — an admin station test, say. */
  | { kind: "icon"; icon: IconType };

type MicPermission = "granted" | "denied" | "prompt" | "unknown";

/**
 * Read before any room exists, so the user finds out the mic is blocked while
 * they can still fix it — LiveKit's own mic state only arrives after the
 * session has started.
 */
export function useMicrophonePermission(): MicPermission {
  const [permission, setPermission] = useState<MicPermission>("unknown");

  useEffect(() => {
    // Safari has no Permissions query for "microphone"; "unknown" is the honest
    // answer there, and we must not prompt for access pre-emptively.
    if (typeof navigator === "undefined" || !navigator.permissions?.query) {
      return;
    }

    let status: PermissionStatus | null = null;
    const onChange = () => {
      if (status) setPermission(status.state as MicPermission);
    };

    navigator.permissions
      .query({ name: "microphone" as PermissionName })
      .then((result) => {
        status = result;
        setPermission(result.state as MicPermission);
        result.addEventListener("change", onChange);
      })
      .catch(() => setPermission("unknown"));

    return () => status?.removeEventListener("change", onChange);
  }, []);

  return permission;
}

function ChecklistRow({
  icon: Icon,
  label,
  tone = "muted",
}: {
  icon: IconType;
  label: string;
  tone?: "muted" | "success" | "warning";
}) {
  const toneClass =
    tone === "success"
      ? "text-osce-success-text"
      : tone === "warning"
        ? "text-osce-warning-text"
        : "text-b2c-text-muted";

  return (
    <li className="flex items-center gap-2">
      <Icon className={cn("h-4 w-4 shrink-0", toneClass)} aria-hidden />
      <span className={cn("text-osce-caption sm:text-osce-body", toneClass)}>
        {label}
      </span>
    </li>
  );
}

/** Mic permission, listening conditions and (optionally) how long this runs. */
export function LivekitReadinessChecklist({
  durationMinutes,
  className = "",
}: {
  durationMinutes?: number;
  className?: string;
}) {
  const micPermission = useMicrophonePermission();

  const micRow =
    micPermission === "denied"
      ? {
          icon: HiOutlineExclamationTriangle,
          label: "Microphone blocked. Allow access in your browser",
          tone: "warning" as const,
        }
      : micPermission === "granted"
        ? {
            icon: HiOutlineCheckCircle,
            label: "Microphone ready",
            tone: "success" as const,
          }
        : {
            icon: HiOutlineMicrophone,
            label: "Your browser will ask for microphone access",
            tone: "muted" as const,
          };

  return (
    <ul
      className={cn("flex flex-col items-start gap-1.5 text-left", className)}
    >
      <ChecklistRow {...micRow} />
      <ChecklistRow
        icon={HiOutlineSpeakerWave}
        label="Headphones and a quiet room work best"
      />
      {durationMinutes ? (
        <ChecklistRow
          icon={HiOutlineClock}
          label={`About ${durationMinutes} minutes`}
        />
      ) : null}
    </ul>
  );
}

/**
 * Avatar inside concentric rings. The rings are an abstract voice motif rather
 * than any depiction of a person: they repeat on every surface, so they have to
 * stay a texture. The avatar itself matches {@link AthenaIdentity} so a patient
 * and Athena read as the same system.
 */
export function LivekitAvatarMotif({
  avatar,
  size = "md",
  className = "",
}: {
  avatar: LivekitIdleAvatar;
  /** `sm` is for surfaces that keep the motif on screen while something else
      needs the vertical space — a live consultation, say. */
  size?: "md" | "sm";
  className?: string;
}) {
  const ringSizes = [46, 60, 74];
  const small = size === "sm";

  return (
    <div
      className={cn(
        "relative flex items-center justify-center",
        small ? "h-16 w-16" : "h-32 w-32 sm:h-36 sm:w-36",
        className,
      )}
    >
      <svg
        viewBox="0 0 160 160"
        className="pointer-events-none absolute inset-0 h-full w-full text-osce-accent"
        aria-hidden
        focusable="false"
      >
        {ringSizes.map((radius, index) => (
          <circle
            key={radius}
            cx="80"
            cy="80"
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            opacity={0.22 - index * 0.06}
          />
        ))}
      </svg>
      {avatar.kind === "image" ? (
        <Image
          src={avatar.src}
          alt={avatar.alt}
          width={72}
          height={72}
          className={cn(
            "shrink-0 rounded-full border-2 border-osce-accent-subtle object-cover object-top shadow-md",
            small ? "h-9 w-9" : "h-16 w-16 sm:h-[72px] sm:w-[72px]",
          )}
        />
      ) : (
        <span
          className={cn(
            "flex items-center justify-center rounded-full border-2 border-osce-accent-subtle bg-osce-accent-muted font-semibold text-osce-accent shadow-md",
            small
              ? "h-9 w-9 text-osce-caption"
              : "h-16 w-16 text-osce-title sm:h-[72px] sm:w-[72px]",
          )}
          aria-hidden
        >
          {avatar.kind === "monogram" ? (
            avatar.initials
          ) : (
            <avatar.icon className={small ? "h-4 w-4" : "h-7 w-7"} />
          )}
        </span>
      )}
    </div>
  );
}

/** Motif + name + context + readiness, for surfaces with no identity of their own. */
export default function LivekitIdleState({
  avatar,
  title,
  subtitle,
  durationMinutes,
  showReadiness = true,
  className = "",
}: {
  avatar: LivekitIdleAvatar;
  /** Omitted where the avatar alone says who this is (the consultation column). */
  title?: string;
  subtitle?: string;
  durationMinutes?: number;
  showReadiness?: boolean;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex w-full flex-col items-center gap-4 px-2 py-2 text-center sm:px-0",
        className,
      )}
    >
      <LivekitAvatarMotif avatar={avatar} />

      {title ? (
        <div className="min-w-0">
          <p className={cn(b2cGroupedRowTitle, "truncate font-semibold")}>
            {title}
          </p>
          {subtitle ? (
            <p className={cn(b2cBodyTextMuted, "mt-0.5")}>{subtitle}</p>
          ) : null}
        </div>
      ) : null}

      {showReadiness ? (
        <LivekitReadinessChecklist durationMinutes={durationMinutes} />
      ) : null}
    </div>
  );
}
