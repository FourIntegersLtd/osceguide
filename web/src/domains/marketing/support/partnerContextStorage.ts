import type { ParsedReferralParams } from "./partnerTypes";

export const PARTNER_CONTEXT_STORAGE_KEY = "osce_partner_context";

export interface StoredPartnerContext {
  partner: ParsedReferralParams["partner"];
  exam: ParsedReferralParams["exam"];
  utmMedium: string | null;
  utmCampaign: string | null;
  refId: string | null;
  savedAt: number;
}

type StorageLike = Pick<Storage, "getItem" | "setItem" | "removeItem">;

const defaultStorage = (): StorageLike | null => {
  if (typeof window === "undefined") return null;
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
};

export function savePartnerContext(
  parsed: ParsedReferralParams,
  storage: StorageLike | null = defaultStorage(),
): void {
  if (!storage) return;
  const value: StoredPartnerContext = {
    partner: parsed.partner,
    exam: parsed.exam,
    utmMedium: parsed.utmMedium,
    utmCampaign: parsed.utmCampaign,
    refId: parsed.refId,
    savedAt: Date.now(),
  };
  try {
    storage.setItem(PARTNER_CONTEXT_STORAGE_KEY, JSON.stringify(value));
  } catch {
    // Storage unavailable; the httpOnly acquisition cookie still carries attribution.
  }
}

export function readPartnerContext(
  storage: StorageLike | null = defaultStorage(),
): StoredPartnerContext | null {
  if (!storage) return null;
  try {
    const raw = storage.getItem(PARTNER_CONTEXT_STORAGE_KEY);
    if (!raw) return null;
    const parsed: unknown = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return null;
    const value = parsed as Partial<StoredPartnerContext>;
    if (typeof value.partner !== "string" || typeof value.exam !== "string") {
      return null;
    }
    return {
      partner: value.partner as StoredPartnerContext["partner"],
      exam: value.exam as StoredPartnerContext["exam"],
      utmMedium: value.utmMedium ?? null,
      utmCampaign: value.utmCampaign ?? null,
      refId: value.refId ?? null,
      savedAt: typeof value.savedAt === "number" ? value.savedAt : 0,
    };
  } catch {
    return null;
  }
}

export function clearPartnerContext(
  storage: StorageLike | null = defaultStorage(),
): void {
  try {
    storage?.removeItem(PARTNER_CONTEXT_STORAGE_KEY);
  } catch {
    // ignore
  }
}
