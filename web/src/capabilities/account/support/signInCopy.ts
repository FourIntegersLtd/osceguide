/** Words the sign-in board draws, kept as data so a test can assert them literally. */

/** Shown once under the form for a wrong email or password (`invalid_credentials`). */
export const WRONG_DETAILS_MESSAGE = "That email or password is not right.";

/** The forced first password change after a temporary password. */
export const FORCED_PASSWORD_COPY = {
  labels: {
    currentPassword: "Temporary password",
    newPassword: "New password",
    confirmPassword: "Confirm it",
  },
  submit: "Save password",
} as const;

export type PasswordCopy = typeof FORCED_PASSWORD_COPY;
