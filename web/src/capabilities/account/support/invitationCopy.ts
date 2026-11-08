import { assessWordsFor } from "@/capabilities/assess-words/vocabulary";

/** The accept-invitation page's subtitle: names the organisation when the lookup found one. */
export function invitationSubtitle(organisationName: string | null): string {
  return organisationName
    ? `${organisationName} has invited you. Choose a password to join.`
    : "Your organisation has invited you. Choose a password to join.";
}

export type InvitationFacts = { organisationName: string | null; orgType: string | null; role: string | null };

/**
 * What the accept-invitation page says. The page sits outside any workspace, so the invitation's
 * organisation kind picks the words: an employer's people are candidates and assessors. Without a
 * known role the plain wording stays; only an employer's heading and button change.
 */
export function invitationView({ organisationName, orgType, role }: InvitationFacts): {
  title: string;
  subtitle: string;
  action: string;
} {
  const hire = orgType === "employer";
  const w = assessWordsFor(hire ? "hire" : "assess");
  const named = hire && organisationName;
  const title = named ? `${organisationName} invited you` : organisationName ? `Join ${organisationName}` : "Accept your invitation";
  const action = named ? `Join ${organisationName}` : "Accept invitation";
  const join = hire ? undefined : "Choose a password to join.";
  if (role === "trainee") {
    return { title, action, subtitle: `You are joining as a ${w.trainee}. ${join ?? "Choose a password to see your assessment."}` };
  }
  if (role === "supervisor") {
    return {
      title,
      action: hire ? "Join as an assessor" : action,
      subtitle: `You are joining as ${hire ? "an" : "a"} ${w.supervisor}. ${join ?? "You will mark candidates on the stations you are given."}`,
    };
  }
  if (role === "admin") {
    return { title, action, subtitle: `You are joining as an administrator. ${join ?? "Choose a password to manage your organisation."}` };
  }
  return { title, action, subtitle: invitationSubtitle(organisationName) };
}
