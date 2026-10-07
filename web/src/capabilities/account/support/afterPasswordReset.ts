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
  signIn: () => Promise<boolean>;
}): Promise<"signed_in" | "sign_in_next"> {
  await deps.endLocalSession();
  if (!deps.invitation) return "sign_in_next";
  return (await deps.signIn()) ? "signed_in" : "sign_in_next";
}
