/** The accept-invitation page's subtitle: names the organisation when the lookup found one. */
export function invitationSubtitle(organisationName: string | null): string {
  return organisationName
    ? `${organisationName} has invited you. Choose a password to join.`
    : "Your organisation has invited you. Choose a password to join.";
}
