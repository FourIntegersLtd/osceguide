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
