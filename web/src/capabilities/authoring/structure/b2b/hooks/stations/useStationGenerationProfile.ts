"use client";

import { useEffect, useState } from "react";
import {
  getStationGenerationProfile,
  type StationGenerationProfileDetail,
} from "@/capabilities/authoring/structure/b2b/lib/api/stationGenerationProfiles";

export function useStationGenerationProfile(profileKey: string | undefined) {
  const [detail, setDetail] = useState<StationGenerationProfileDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const key = profileKey?.trim();
    if (!key) {
      setDetail(null);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    void getStationGenerationProfile(key)
      .then((next) => {
        if (!cancelled) setDetail(next);
      })
      .catch(() => {
        if (!cancelled) {
          setDetail(null);
          setError("Could not load draft-writing guides for this exam.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [profileKey]);

  return {
    blockHints: detail?.blockHints ?? {},
    systemPrompt: detail?.systemPrompt ?? "",
    loading,
    error,
  };
}
