# platform-web dev performance baseline

How to compare local dev speed before/after layout chunking changes.

## What changed (layout critical path)

- `SurfaceShell` imports `navFooters.ts`, not `screens.ts`.
- Screen maps load per arm via dynamic `import()` in `src/surfaces/screens.ts`.
- Institution-style shells use `LazyHelpPanel` so LiveKit is not in the shell module graph.

## Measure startup

From `platform-web/`:

```bash
rm -rf .next
node scripts/measure-dev-startup.mjs          # Turbopack (default dev)
node scripts/measure-dev-startup.mjs --webpack
```

The script prints seconds until `http://127.0.0.1:3100/` responds.

## Measure first route compile

1. Start `npm run dev`.
2. Open `/app/me/dashboard` (signed in) or any workspace route you use daily.
3. Note the terminal line `Compiling /app/...` duration on first hit.
4. Navigate to 3–4 other nav items; second visits should compile less or reuse chunks.

## Environment notes

Record Node version (`node -v`), machine RAM, and whether legacy `frontend/` dev is also running (extra file watchers).
