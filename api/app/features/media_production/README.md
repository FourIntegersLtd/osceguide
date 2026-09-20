# media_production

Async audio/video production for study material (B2C parity).

## Routes (platform admin)

| Method | Path | Kind |
|--------|------|------|
| POST | `/api/v1/media/{id}/generate-podcast` | `summary` → `content.podcast_url` |
| POST | `/api/v1/media/{id}/regenerate-av` | `slide_deck` → TTS + video → `final_video_url` |
| POST | `/api/v1/media/{id}/generate-audio` | `podcast` → `content.audio_url` |

Jobs run on the `media` procrastinate queue. Enqueue happens in the same DB transaction as setting `content.status` to a `generating_*` value.

## Local setup

From `backend/platform-api`, copy AV keys from the B2C `.env` (same keys you already use for podcasts/slides):

```bash
poetry run python scripts/sync_av_env_from_b2c.py
```

Run the API (`make start`, port 8002) and the worker (`make worker`) in separate terminals. **ffmpeg** must be on `PATH` for slide video export.

## Environment

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Podcast script |
| `CARTESIA_API_KEY` | TTS |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_S3_BUCKET` / `AWS_REGION` | Upload MP4/MP3 |

The worker host needs **ffmpeg** on `PATH` for MoviePy video export.

Slide video uses the ported B2C `SlideService` (`b2c_slide_service.py`): progressive bullets, layouts, `bg.png`, Poppins fonts, end card, Cartesia bullet segments, and S3 key `teaching_videos/{app_type}/{topic}_{slide_id}.mp4`.

Bundled assets: `assets/slides/images/bg.png`, `assets/fonts/Poppins-*.ttf`. Override fonts with `MEDIA_AV_FONT_DIR` if needed.

## Failure

On worker failure, `content.status` is set to `failed`. Re-run the POST after fixing configuration or content.
