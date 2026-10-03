# media_production

## Purpose
Async audio and video production for published study material (B2C parity): summary
podcasts, slide-deck AV, and standalone podcast audio. Platform admins trigger work
through `media` routes; this slice enqueues procrastinate jobs and updates the
parent `media` row's `content` JSON when generation finishes or fails.

## Aggregates & invariants
No tables of its own. Work is keyed by a `media` aggregate id.

- Only platform admins may start production (enforced on the HTTP routes in this slice).
- Enqueue and `content.status` transition happen in one transaction so a job is never
  orphaned without a `generating_*` status.
- On worker failure, `content.status` becomes `failed`; the admin re-runs the POST after
  fixing configuration or content.

## Routes
| Method | Path | Kind |
|--------|------|------|
| POST | `/api/v1/media/{id}/generate-podcast` | `summary` → `content.podcast_url` |
| POST | `/api/v1/media/{id}/regenerate-av` | `slide_deck` → TTS + video → `final_video_url` |
| POST | `/api/v1/media/{id}/generate-audio` | `podcast` → `content.audio_url` |

## Jobs
| Task | Queue | Notes |
|------|-------|-------|
| `produce_summary_podcast` | `media` | Script + TTS for a summary |
| `regenerate_slide_av` | `media` | Slide video export (MoviePy + Cartesia) |
| `produce_podcast_audio` | `media` | Audio-only podcast |

Podcasts are voiced by ElevenLabs Eleven v4 (text-to-dialogue). Regenerate them all with
`poetry run python scripts/regenerate_podcasts.py --help`.

Run `make worker` beside `make start`. **ffmpeg** must be on `PATH` for slide video.

## Cross-slice dependencies
- **`media`**: reads and updates the media row and `content` payload.
- **`core.settings`**: model and AV keys (`OPENAI_API_KEY`, `ELEVENLABS_API_KEY` and voice ids, `CARTESIA_API_KEY` for slides, AWS S3).

## Local setup

From `api`, copy AV keys from the B2C `.env`:

```bash
poetry run python scripts/sync_av_env_from_b2c.py
```

Slide video uses the ported B2C `SlideService` (`b2c_slide_service.py`). Bundled assets:
`assets/slides/images/bg.png`, `assets/fonts/Poppins-*.ttf`. Override fonts with
`MEDIA_AV_FONT_DIR` if needed.
