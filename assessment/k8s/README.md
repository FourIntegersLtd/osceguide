# Self-hosted deployment

One Deployment per worker. `configmap.yaml` selects the worker and declares the
backends it may serve (`VOICE_BACKENDS_JSON`); `secret.yaml` (copied from
`secret.example.yaml`) carries the URLs, worker secrets and provider keys.

```sh
kubectl apply -f namespace.yaml -f configmap.yaml -f secret.yaml -f deployment.yaml
kubectl -n assessment-platform rollout status deployment/assessment-worker
```

The container runs `make start`: gunicorn serves `/health` and supervises one
`python -m livekit_assessment_worker.entrypoint start` subprocess.

## Node labels are a prerequisite

Both Deployments require `osceguide.io/livekit-worker=true` on every node they may
run on, and spread one pod per node (`topologySpreadConstraints`,
`whenUnsatisfiable: DoNotSchedule`). A node without the label is invisible to the
scheduler, and a replica with nowhere left to go stays `Pending` rather than
doubling up.

```sh
kubectl get nodes -L osceguide.io/livekit-worker     # every worker node: true
kubectl label node <name> osceguide.io/livekit-worker=true
```

`provision-worker.yml` applies the label; a manual `k3s agent` join does not.
Replicas must not exceed the number of labelled nodes.

## Capacity

`LIVEKIT_*_MAX_CONCURRENT_JOBS` is a *per-pod* cap, so with one pod per node it is
also the per-node admission limit. Each node carries an assessment pod **and** an
assistant pod, so the two budgets add up on the same hardware: a CX33 measured at
~8 comfortable concurrent sessions is split 6 (assessment) + 3 (assistant).

Note the load function counts jobs, not CPU, so a saturated node does not shed
dispatch on its own — the cap is the only backpressure. Re-measure after any
change to the pipeline; see `livekit/k8s/INFRASTRUCTURE.md`.

## Rollouts drain rather than cut

`terminationGracePeriodSeconds: 900` with `maxUnavailable: 0` means a rollout adds
a pod before removing one, and an evicted pod keeps serving its consultations until
they end. The worker's own `drain_timeout` (840s, `LIVEKIT_*_DRAIN_TIMEOUT`) must
stay under the grace period or the kubelet SIGKILLs mid-session. The longest station
is 12 min (`osce_assessment/prompts/consultation_pacing.py`), so expect a pod to sit
`Terminating` for that long — this is correct, not a stuck rollout.

Liveness probes are intentionally omitted: a restart would cut every session on the
pod, and the supervisor's `/health` reports gunicorn rather than whether the agent is
still registered with LiveKit, so it cannot detect the failure it would be there for.
