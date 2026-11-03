---
name: commons-images
description: Find free-to-use (commercial-OK) Wikimedia Commons images, such as X-rays and clinical photos, to sit beside the images already in a legacy Firestore station collection (default ortho_stations). Licence checked twice, attribution recorded, side-by-side report. Never deletes or replaces existing images. Use when asked to source, replace or audit station images, or to check whether images are free to use.
---

# Commons images for stations

Script: `.claude/skills/commons-images/scripts/commons_images.py` (stdlib only). Run it from the repo
root. Everything is written to a work folder (default `commons-work/`, which is gitignored by
convention: do not commit downloaded images without the user's say-so).

## Rules
- **Never delete, overwrite or re-upload an existing image**, in Firestore, Storage or on disk.
  Firestore is read-only here.
- **Commercial use only.** Accept CC0, public domain, CC BY, CC BY-SA. Reject NC, ND, GFDL-only,
  fair use, "no licence", anything marked NonFree, and any file whose page carries a deletion,
  copyvio, no-permission or licence-review flag. The script does this; you do not override it.
- **Two checks.** `search` checks the licence metadata and the page's categories and templates.
  `fetch` checks again live before it downloads. A file that fails either is not used.
- **Restrictions** (personality rights, trademarks) fail the check and need a human to look.
- **Patient privacy.** Look at every approved image yourself (Read the downloaded file). Reject any
  with a visible name, date of birth, hospital number or face.
- **Existing images have unknown licences.** Say so in the report. Do not claim they are free to
  use; the user has to trace their source.
- Commons licences are declared by uploaders. The checks lower the risk; they are not legal
  advice. Say this when you report.

## Steps
1. **Extract** the existing images (every image URL anywhere in each station document):
   - live, read-only: `cd api && FIREBASE_SERVICE_ACCOUNT_KEY_PATH="$PWD/../service-key" poetry run python ../.claude/skills/commons-images/scripts/commons_images.py --work ../commons-work extract --from-firestore --app-type ortho --api-dir .`
     The key is `service-key` at the repo root (gitignored); `api/.env` does not carry it. Pass the
     path only; never print or open the key. Ortho stations keep their image in `radiograph_image_url`.
   - or from an export: `... extract --export path/to/stations.json --app-type ortho`
     (make one with `poetry run python scripts/import_b2c_stations.py --from-firestore --collection ortho --write-export ./export`).
   If this fails for credentials, stop and ask the user. Do not hunt for other keys.
2. **Write queries.** Read `commons-work/existing.json`. For each station, write 1–3 specific
   Commons search terms for the finding the image should show (for example
   `"distal radius fracture radiograph"`, `"Colles fracture X-ray"`). Look at the existing image
   (Read its URL if it is reachable) to match the view and finding. Save
   `commons-work/queries.json` as `{"<station_id>": ["term", ...]}`.
3. **Search:** `... search --queries commons-work/queries.json`. Writes `candidates.json`. It also
   traces each existing image: many were copied from Commons, so it looks the filename up there
   (any extension case) and records that file's licence. A match is by name only: say "confirm it is
   the same picture", and note near-misses by eye (e.g. an S3 copy with a `1` appended).
4. **Pick.** For each station, choose up to 3 passing candidates that show the right finding, view
   and body part (open the `thumb_url`). Save `commons-work/approved.json` as
   `{"<station_id>": ["File:....jpg", ...]}`.
5. **Fetch:** `... fetch --approved commons-work/approved.json`. Re-checks, downloads to
   `commons-work/commons/<station_id>/`, writes `manifest.json`.
6. **Privacy check:** Read each downloaded image (a labelled contact sheet of 12 per page, made with
   PIL from api's Poetry env, keeps this to a few reads). Drop any with identifiers from `approved.json`,
   delete only that downloaded file, and re-run `fetch`.
7. **Report:** `... report` writes `report.html` (existing left, Commons right) and
   `ATTRIBUTION.md`. Publish `report.html` as an artifact if the user wants to share it.
8. **Publish** (only when the user asks; additive, idempotent, dry run unless `--apply`). From `api/`,
   with `P=../.claude/skills/commons-images/scripts/publish_images.py`:
   - `poetry run python $P s3 --apply`: uploads to `station_images/ortho/<station>/<file>`, sets `s3_url`.
   - `GRPC_DNS_RESOLVER=native FIREBASE_SERVICE_ACCOUNT_KEY_PATH="$PWD/../service-key" PYTHONPATH=. poetry run python $P firestore --apply`:
     every image with its credit goes to `commons_images`; only CC0 / public-domain URLs join
     `additional_image_urls`, because the legacy site renders those bare, with no credit.
     (Without the native resolver, gRPC can fail with "Could not contact DNS servers".)
   - `PYTHONPATH=. railway run -s platform-postgres -e staging poetry run python $P platform --database-url-env RAILWAY_PROXY --apply`:
     a new published version per station; `additional_image_urls` gains `{url, kind, caption, alt}`.
     It matches on the document's own `station_id` (a uuid), mapped through `stations.json`.
   - Production (`-s platform-postgres-production -e production`) may lag `main`'s schema
     (`UndefinedColumn`). Then run the script from a worktree of `origin/production-api`:
     `railway run ... sh -c "cd <worktree>/api && PYTHONPATH=. $(poetry env info -p)/bin/python $P platform --work <abs commons-work> ..."`.
   - Prove it: re-run each without `--apply`; every station should say `same`.

## Report back
Per station: existing image count, Commons images kept, licence of each, anything rejected and
why. Then: the attribution the app must show (CC BY / BY-SA), the share-alike note (edits to a
BY-SA image, e.g. crops with arrows, must be released under BY-SA), and that existing images'
licences are still unknown.
