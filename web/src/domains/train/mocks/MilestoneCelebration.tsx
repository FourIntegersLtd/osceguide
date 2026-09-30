"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Confetti } from "@/foundation/ui";
import { checkMilestone } from "@/domains/train/mocks/model";

const PREVIOUS_COUNT_KEY = "prev_station_count";

/**
 * The confetti, badge and cheer when this session crossed a milestone.
 *
 * The count is remembered in the browser, as the old client did, so a reload
 * does not celebrate the same milestone twice.
 */
export function MilestoneCelebration({ stationsCompleted }: { stationsCompleted: number }) {
  const [showConfetti, setShowConfetti] = useState(false);
  const [achievement, setAchievement] = useState({ title: "", message: "" });
  const celebrated = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const badgeCount = checkMilestone(stationsCompleted, 0).stationBadges;

  useEffect(() => {
    if (celebrated.current || stationsCompleted === 0) return;
    celebrated.current = true;

    let previous = 0;
    try {
      previous = Number.parseInt(window.localStorage.getItem(PREVIOUS_COUNT_KEY) ?? "0", 10) || 0;
    } catch {
      // A browser with storage blocked simply never celebrates twice.
    }

    const { reached } = checkMilestone(stationsCompleted, previous);
    if (!reached) return;

    setAchievement({
      title: "NEW MILESTONE UNLOCKED!",
      message: `You've completed ${stationsCompleted} stations! (${badgeCount} badges)`,
    });
    setShowConfetti(true);
    const audio = audioRef.current;
    if (audio) {
      audio.volume = 0.3;
      audio.currentTime = 0;
      // Autoplay may be refused; the confetti still shows.
      audio.play().catch(() => undefined);
    }
    try {
      window.localStorage.setItem(PREVIOUS_COUNT_KEY, String(stationsCompleted));
    } catch {
      // ignore
    }
  }, [stationsCompleted, badgeCount]);

  const close = useCallback(() => setShowConfetti(false), []);

  return (
    <>
      {/* A cheer with no words in it: there is nothing to caption. */}
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <audio ref={audioRef} src="/sounds/crowd-cheers.mp3" preload="auto" />
      <Confetti
        isActive={showConfetti}
        title={achievement.title}
        message={achievement.message}
        badgeCount={badgeCount}
        onClose={close}
      />
    </>
  );
}
