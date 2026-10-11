/** The largest profile photo the server accepts, in bytes. */
export const AVATAR_MAX_BYTES = 5 * 1024 * 1024;

export const AVATAR_CAPTION = "JPG or PNG, 5 MB max";

export const AVATAR_TOO_BIG = "That photo is over 5 MB. Choose a smaller JPG or PNG.";

/** The photo button says what it will do: add the first one, or change the one there. */
export function avatarButtonLabel(hasAvatar: boolean): string {
  return hasAvatar ? "Change photo" : "Add photo";
}

/** A file over the limit is refused here, before an upload that would only fail. */
export function avatarTooBig(sizeBytes: number): boolean {
  return sizeBytes > AVATAR_MAX_BYTES;
}
