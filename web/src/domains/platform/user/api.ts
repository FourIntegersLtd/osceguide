import { platformRequest } from "@/foundation/platform-client";

// until regenerated: POST /platform/users/{id}/temporary-password.
export function reissueTemporaryPassword(userId: string, temporaryPassword: string): Promise<void> {
  return platformRequest<void>(`/api/v1/platform/users/${encodeURIComponent(userId)}/temporary-password`, {
    method: "POST",
    body: { temporary_password: temporaryPassword },
  });
}

// until regenerated: POST /platform/users/{id}/reset-mfa (204).
export function resetUserMfa(userId: string): Promise<void> {
  return platformRequest<void>(`/api/v1/platform/users/${encodeURIComponent(userId)}/reset-mfa`, {
    method: "POST",
  });
}
