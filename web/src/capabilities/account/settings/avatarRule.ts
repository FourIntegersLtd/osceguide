/** The largest profile photo the server accepts. */
export const AVATAR_MAX_MB = 5;

export const AVATAR_MAX_BYTES = AVATAR_MAX_MB * 1024 * 1024;

export const AVATAR_CAPTION = `JPG or PNG, ${AVATAR_MAX_MB} MB max`;

export const AVATAR_TOO_BIG = `That photo is over ${AVATAR_MAX_MB} MB. Choose a smaller JPG or PNG.`;
