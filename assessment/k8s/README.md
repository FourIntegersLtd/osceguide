# Self-hosted deployment

One Deployment per worker, in two environments on the same K3s cluster:

| Environment | Namespace | LiveKit Cloud project | Backend | Changes when |
|---|---|---|---|---|
| staging | `assessment-platform-staging` | `new-test-agent` | `staging-api.osceguide.com` | CI passes on `main` (automatic) |
| production | `assessment-platform` | the live project | the live backends | someone runs **Promote workers to production** |

## Layout

```
k8s/
  base/                  what every environment shares
    namespace.yaml         (renamed by each overlay)
    networkpolicy.yaml
    configmap.yaml         assessment worker settings + VOICE_BACKENDS_JSON
    configmap-assistant.yaml
    deployment.yaml        assessment worker
    deployment-assistant.yaml
  overlays/
    staging/             namespace, 1 replica each, small session caps, Sentry "staging"
    production/          namespace, base capacity, Sentry "production"
  secret.example.yaml    template for each namespace's secret, applied by hand
```

The configmaps select the worker and declare the backends it may serve
(`VOICE_BACKENDS_JSON`); each namespace's `assessment-worker-secrets` carries the
URLs, worker secrets and provider keys. Secrets are never in an overlay: they hold
real keys and are created by hand once per namespace (below).

To see exactly what an environment receives, or to apply it by hand:

```sh
kubectl kustomize k8s/overlays/staging          # render only, touches nothing
kubectl apply -k k8s/overlays/staging           # apply (the workflows do this for you)
kubectl -n assessment-platform-staging rollout status deployment/assessment-worker
```

A hand-run apply uses the moving `:staging` / `:production` image tag, which always
points at what that environment last ran successfully. The workflows instead pin the
exact image digest and stamp the commit (`osceguide.io/commit` annotation), so

```sh
kubectl -n assessment-platform get deploy -o jsonpath='{range .items[*]}{.metadata.name} {.metadata.annotations.osceguide\.io/commit}{"\n"}{end}'
```

answers "which commit is production running?".

## How a change reaches production

1. Merge to `main` a change under `assessment/`. CI assessment runs, then
   `publish-workers.yml` builds
   `ghcr.io/fourintegersltd/osceguide-assessment-platform:<sha>` and rolls it out
   to **staging** (when the repository variable `K8S_AUTO_DEPLOY` is `true`).
2. Test on staging: the staging site and API dispatch into `new-test-agent`, which
   only the staging workers serve.
3. GitHub → Actions → **Promote workers to production** → Run workflow (from `main`). Leave
   the commit empty to ship what staging runs. The `check` job refuses unless the
   commit is on `main`, CI passed on it, and both staging workers run that exact
   image and are available. The `deploy` job then rolls the same image out to
   production, re-points `:production`, and moves the `production-workers` branch forward
   to the commit.

Promote order when a change spans apps: api, then workers, then web.

## Rolling production back

Run **Promote workers to production** with `rollback` ticked and `commit_sha` set to the
commit production ran before (any commit on the `production-workers` branch). Its image
already exists, so nothing is rebuilt; the staging check and branch move are skipped.
Live consultations drain first, so allow up to ~15 minutes per worker.

If GitHub itself is unavailable, on the control plane:

```sh
kubectl -n assessment-platform rollout undo deployment/assessment-worker
kubectl -n assessment-platform rollout undo deployment/assistant-worker
```

## Setting up an environment

Done once per namespace, on the control plane. The deploy refuses to run until both
secrets exist (`scripts/k8s_rollout_on_control_plane.sh` checks first).

```sh
NAMESPACE=assessment-platform-staging

# 1. The namespace (the first deploy would create it too; the secrets need it now).
kubectl create namespace "$NAMESPACE"

# 2. The registry pull secret: the same GHCR credentials production uses, copied across.
kubectl -n assessment-platform get secret ghcr-pull-credentials -o json \
  | jq 'del(.metadata.namespace, .metadata.uid, .metadata.resourceVersion, .metadata.creationTimestamp, .metadata.ownerReferences, .metadata.annotations)' \
  | kubectl -n "$NAMESPACE" apply -f -

# 3. The worker secrets, from the template, with this environment's values.
#    Copy the template up first: scp k8s/secret.example.yaml <control-plane>:secret.staging.yaml
#    then fill it in there (never in the repo checkout).
kubectl -n "$NAMESPACE" apply -f secret.staging.yaml
shred -u secret.staging.yaml                   # don't leave keys lying on disk
```

Staging's values, and nothing else:

| Key | Staging value |
|---|---|
| `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` | the **`new-test-agent`** project's |
| `PLATFORM_API_URL` | `https://staging-api.osceguide.com` |
| `PLATFORM_WORKER_SECRET` | a fresh value, equal to staging platform-api's `WORKER_SECRET`. Never production's |
| `PRACTICE_API_URL`, `INSTITUTION_API_URL` and their secrets | **empty**. The legacy backends have no staging; an empty URL only fails if that backend is dispatched, which staging never does |
| provider keys (`OPENAI_API_KEY`, ...) | may be the same accounts as production, or separate keys to see staging spend apart |
| `SENTRY_DSN` | same project is fine: the overlay labels errors `staging` |

Never put a production LiveKit key or a production backend URL in the staging
secret: staging would then take real candidates' dispatches or write into real data.

### One-time GitHub setup (repository settings)

- **Environments** `staging-workers` and `production-workers` record each deploy
  (in the old repository they were `staging` and `production`). They have no
  rules: this is a private repository on a free plan,
  where GitHub offers neither required reviewers nor branch protection. Today only
  the owner can run workflows, so running **Promote workers to production** is the
  approval. If someone else gets write access, upgrade the plan and add the owner as
  a required reviewer on `production-workers`, plus a rule on the `production-workers` branch
  blocking force pushes and deletion.
- Repository secrets `K8S_CONTROL_PLANE_HOST` and `K8S_CONTROL_PLANE_SSH_KEY` are
  shared by both environments. Optional variables: `K8S_MANIFEST_DIR` (control-plane
  folder holding one sub-folder per environment, default
  `/root/k8s/assessment-platform`) and `ROLLOUT_TIMEOUT_SECS`.

The container's only process is the worker (`python -m hosting.run_worker start`,
PID 1). The LiveKit SDK inside it serves the probes on the worker's own port
(`/` on 8087 for assessment, 8088 for assistant), and it receives the kubelet's
SIGTERM directly: it stops taking new sessions at once, lets the running ones
finish, and exits, so a pod leaves as soon as its last session ends.

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

The one-pod-per-node rule only counts pods in the same namespace, so a staging pod
shares a node with a production pod. That is why staging runs 1 replica with caps of
2 + 1: a busy staging test takes at most 3 sessions' worth of a node from production.
Check headroom before raising them.

**platform-api's waiting line must match.** platform-api admits assessment sessions
onto these workers itself and queues candidates once `LIVEKIT_SELF_HOSTED_SEATS` are
taken (`app/features/voice/seats.py`). That setting must equal replicas ×
`LIVEKIT_ASSESSMENT_MAX_CONCURRENT_JOBS` for the environment, on both the Railway
api and worker services:

| Environment | Replicas × per-pod cap | `LIVEKIT_SELF_HOSTED_SEATS` |
|---|---|---|
| production | 3 × 6 | 18 (the default) |
| staging | 1 × 2 | 2 |

Set it too high and the candidate past the real limit joins an empty room that no
worker accepts. Set it too low and people wait while pods sit idle. Change it in the
same change as the replicas or the cap.

## Rollouts drain rather than cut

`terminationGracePeriodSeconds: 900` with `maxUnavailable: 0` means a rollout adds
a pod before removing one, and an evicted pod keeps serving its consultations until
they end. The worker's own `drain_timeout` (840s, `LIVEKIT_*_DRAIN_TIMEOUT`) must
stay under the grace period or the kubelet SIGKILLs mid-session. The longest station
is 12 min (`osce_assessment/prompts/consultation_pacing.py`), so a pod with a session
in progress can sit `Terminating` for up to that long. That is correct, not a stuck
rollout. A draining pod takes no new sessions, and an idle pod exits within seconds.
If an idle pod sits `Terminating` for the full 15 minutes, the stop signal is not
reaching the worker: check that the container's main process is the worker itself.

Liveness probes are intentionally omitted: a restart would cut every session on the
pod. A worker that exits on its own is restarted by the kubelet anyway, because it is
the container's main process.
