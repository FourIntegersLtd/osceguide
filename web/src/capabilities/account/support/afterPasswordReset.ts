/**
 * What happens once a reset link has set a new password.
 *
 * The reset ends every refresh chain the account holds, so a session
 * this browser still held is dead at the backend while its cookies live on.
 * `/login` then saw "signed in" and bounced to `/app`, where every call
 * answered 401. The local session is ended first, always; then an invitation
 * signs the new account in with the password just chosen, and a plain reset
 * goes back to sign-in.
 */
export async function afterPasswordReset(deps: {
  invitation: boolean;
  endLocalSession: () => Promise<void>;
  signIn: () => Promise<"signed_in" | "second_step" | "failed">;
}): Promise<"signed_in" | "sign_in_next" | "second_step" | "sign_in_failed"> {
  await deps.endLocalSession();
  if (!deps.invitation) return "sign_in_next";
  const outcome = await deps.signIn();
  return outcome === "failed" ? "sign_in_failed" : outcome;
}
