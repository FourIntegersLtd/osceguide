/**
 * Assess seams. Everything a sitting needs that a voice room would normally
 * produce is done through the api instead: starting a circuit works locally,
 * advancing it does not (LiveKit), so a journey starts the circuit and then
 * ends it, which completes the sitting without any station being spoken.
 */
import { call, login, orgPath, PASSWORD, switchWorkspace } from "./api";
import { world } from "./world";

export interface BuiltSitting {
  id: string;
  circuitId: string;
  slotId: string;
  token: string;
}

export async function adminToken(): Promise<string> {
  const w = world();
  return switchWorkspace(await login(w.accounts.admin.email, PASSWORD), w.slug);
}

/** A sitting with one circuit, the roster trainee on it, not yet started. */
export async function buildSitting(name: string, mode: "exam" | "training"): Promise<BuiltSitting> {
  const w = world();
  const token = await adminToken();
  const sitting = await call(token, orgPath(w.slug, `/sittings`), {
    method: "POST",
    body: {
      name,
      mode,
      sitting_type: mode === "exam" ? "mock_exam" : "group_training",
      programme_id: w.programmeId,
      scheduled_for: new Date(Date.now() + 86_400_000).toISOString(),
    },
  });
  const circuit = await call(token, orgPath(w.slug, `/sittings/${sitting.id}/circuits`), {
    method: "POST",
    body: {
      name: `${name} circuit`,
      station_version_ids: w.stationVersionIds.slice(0, 1),
      trainee_ids: [w.traineeUserId],
      timing: { reading_minutes: 1, simulation_minutes: 5 },
    },
  });
  const slotId = await firstSlotId(token, circuit.id as string);
  return { id: sitting.id as string, circuitId: circuit.id as string, slotId, token };
}

async function firstSlotId(token: string, circuitId: string): Promise<string> {
  const slug = world().slug;
  const console_ = await call(token, orgPath(slug, `/circuits/${circuitId}/console`));
  const slot = ((console_.slots ?? []) as { id: string }[])[0];
  if (!slot) throw new Error(`circuit ${circuitId} has no slots: ${Object.keys(console_).join(",")}`);
  return slot.id;
}

export const startCircuit = (s: BuiltSitting) =>
  call(s.token, orgPath(world().slug, `/circuits/${s.circuitId}/start`), { method: "POST" });

export const endCircuit = (s: BuiltSitting) =>
  call(s.token, orgPath(world().slug, `/circuits/${s.circuitId}/end`), { method: "POST" });
