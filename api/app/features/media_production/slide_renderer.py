"""B2C MoviePy slide renderer (ported from b2c.shared.services.slide_service)."""

from __future__ import annotations

import json
import re
import textwrap
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import boto3
from cartesia import Cartesia
from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
    concatenate_audioclips,
    concatenate_videoclips,
)
from moviepy.video.fx import CrossFadeIn

from app.core.logging import get_logger
from app.features.media_production.slide_models import BulletAudioSegment, SlideGenerationResponse

if TYPE_CHECKING:
    from app.core.settings import Settings

log = get_logger(__name__)

# Unused when firestore_service is None (platform AV jobs).
COLLECTION_MAPPING: dict = {}

SLIDE_GENERATION_PROMPT = ""


def set_nested_value(document: dict, key: str, new_value) -> None:
    parts = key.split(".")
    target = document
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    target[parts[-1]] = new_value


def utc_now_iso_z() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


openai_client = None


class SlideService:

    def __init__(self, firestore_service=None, settings: Settings | None = None):
        from app.core.settings import get_settings

        self.settings = settings or get_settings()
        self.openai_client = openai_client
        self.firestore_service = firestore_service

        cartesia_key = self.settings.cartesia_api_key.strip()
        if cartesia_key:
            self.cartesia_client = Cartesia(api_key=cartesia_key)
            self.voice_id = "00967b2f-88a6-4a31-8153-110a92134b9f"  # Asher, male voice
            self.model_id = "sonic-3"
            self.output_format = {
                "container": "wav",
                "encoding": "pcm_f32le",
                "sample_rate": 44100,
            }
            log.debug("Cartesia TTS initialized")
        else:
            self.cartesia_client = None
            log.warning("Cartesia API key not found - audio generation disabled")

        assets_dir = Path(__file__).resolve().parent / "assets"
        self.slides_base_dir = assets_dir / "slides"
        self.slides_base_dir.mkdir(parents=True, exist_ok=True)
        font_dir = (
            Path(self.settings.media_av_font_dir)
            if self.settings.media_av_font_dir.strip()
            else assets_dir / "fonts"
        )
        self.font_path = font_dir / "Poppins-Regular.ttf"
        self.bold_font_path = font_dir / "Poppins-Medium.ttf"

        self._s3_bucket = self.settings.aws_s3_bucket
        self._aws_region = self.settings.aws_region
        self.s3_client = boto3.client(
            service_name="s3",
            region_name=self._aws_region,
            aws_access_key_id=self.settings.aws_access_key_id,
            aws_secret_access_key=self.settings.aws_secret_access_key,
        )
        self.s3_base_folder = "teaching_videos"

    def _create_topic_folder(self, topic: str, slide_id: str) -> Path:
        """
        Create a topic-specific folder with audio and json subfolders.

        Args:
            topic: The topic name (will be sanitized for folder name)
            slide_id: The slide job ID

        Returns:
            Path: Path to the topic folder
        """
        # Sanitize topic for folder name
        safe_topic = "".join(
            character if character.isalnum() or character in (" ", "-", "_") else "_" for character in topic
        )
        safe_topic = safe_topic.replace(" ", "_").lower()[:50]  # Limit length

        # Create folder structure: slides/<topic>_<slide_id>/
        topic_folder = self.slides_base_dir / f"{safe_topic}_{slide_id}"
        topic_folder.mkdir(parents=True, exist_ok=True)

        # Create subfolders
        (topic_folder / "audio").mkdir(exist_ok=True)

        log.debug(f"Created topic folder: {topic_folder}")
        return topic_folder

    def _normalize_slides_array(self, slide_data: dict):
        """
        Convert the 'slides' field from a dict with numeric keys to a sorted list.
        This handles a Firestore quirk where arrays can be stored as objects.

        Args:
            slide_data: The dictionary containing the slide data.
        """
        if isinstance(slide_data, dict) and "slides" in slide_data:
            slides_field = slide_data["slides"]
            if isinstance(slides_field, dict) and not isinstance(slides_field, list):
                # Check if it's a dict with numeric string keys
                keys = list(slides_field.keys())
                if keys and all(field_key.isdigit() for field_key in keys):
                    log.debug("[SLIDE_SERVICE] Normalizing slides field from dict to list")
                    sorted_keys = sorted(keys, key=int)
                    slide_data["slides"] = [slides_field[field_key] for field_key in sorted_keys]
                    log.debug(f"[SLIDE_SERVICE] Converted to list with {len(slide_data['slides'])} items")

    def _save_slides_json(self, slide_data: dict, topic_folder: Path, slide_id: str) -> Path:
        """
        Save slide data as JSON in the topic folder.

        Args:
            slide_data: Complete slide data dictionary
            topic_folder: Path to the topic folder
            slide_id: The slide job ID

        Returns:
            Path: Path to the saved JSON file
        """
        json_path = topic_folder / f"slides_{slide_id}.json"

        with open(json_path, "w", encoding="utf-8") as handle:
            json.dump(slide_data, handle, indent=2, ensure_ascii=False)

        log.debug(f"Saved slides JSON: {json_path}")
        return json_path

    def generate_slides(
        self,
        prompt: str,
        user_id: str = None,
        app_type: str = "sca",
        specialty: str = None,
    ) -> dict:
        """
        Generate AI-narrated teaching video slides from a given scenario.

        Args:
            prompt: The scenario to generate slides for
            user_id: Optional user ID of the creator
            app_type: App type (sca, plab, casc) - defaults to "sca"

        Returns:
            dict: Generated slide data with status and slide_id, or error message
        """
        if not prompt or not isinstance(prompt, str):
            log.error("Invalid or missing prompt")
            return {"error": "Invalid or missing prompt"}, 400

        log.debug(f"[SLIDE_GENERATION] Starting slide generation for prompt: {prompt[:100]}...")

        # Construct user prompt
        user_prompt = f"Generate teaching slides based on the following clinical scenario: {prompt}"

        log.debug(f"User prompt: {user_prompt}")

        messages = [
            {"role": "system", "content": SLIDE_GENERATION_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        try:
            log.debug("[SLIDE_GENERATION] Calling OpenAI API for structured slide generation")

            completion = self.openai_client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=messages,
                response_format=SlideGenerationResponse,
            )

            slide_response = completion.choices[0].message.parsed
            log.debug(f"[SLIDE_GENERATION] Successfully generated {len(slide_response.slides)} slides")

            # Generate a unique ID for the slide job
            slide_id = f"slide_{str(uuid.uuid4())[:8]}"

            # Add metadata to the slide response
            self._add_slide_metadata(slide_response, slide_id, user_id, specialty)

            # Convert from Pydantic model to Python dict for storage/return
            slide_data = slide_response.model_dump()

            # Create topic-specific folder - topic_<slide_id>
            topic_folder = self._create_topic_folder(slide_response.topic, slide_id)

            # Save to Firestore and then save the JSON
            if self.firestore_service:
                success, firestore_doc_id = self._save_to_firestore(slide_data, app_type)
                if not success:
                    log.warning(
                        "[SLIDE_GENERATION] Failed to save to Firestore, but continuing with local JSON save."
                    )
                else:
                    # Store the Firestore document ID in slide_data for future updates
                    slide_data["firestore_doc_id"] = firestore_doc_id

            # Save the final slide_data to JSON (now contains Firestore ID if available)
            json_path = self._save_slides_json(slide_data, topic_folder, slide_id)

            log.debug(f"[SLIDE_GENERATION] Slide generation completed: {slide_id}")
            log.debug(f"Slides saved to: {json_path}")

            return {
                "message": "Slides generated successfully",
                "slide_id": slide_id,
                "topic": slide_response.topic,
                "about": slide_response.about,
                "slides_count": len(slide_response.slides),
                "status": "draft",
                "topic_folder": str(topic_folder),
                "json_path": str(json_path),
                "data": slide_data,
            }, 200

        except Exception as e:
            log.error(f"[SLIDE_GENERATION] Failed to generate slides: {str(e)}", exc_info=True)
            return {"error": f"Slide generation failed: {str(e)}"}, 500

    def _add_slide_metadata(
        self,
        slide_response: SlideGenerationResponse,
        slide_id: str,
        user_id: str,
        specialty: str = None,
    ):
        """
        Enrich the slide response object with metadata.

        Args:
            slide_response: The SlideGenerationResponse object from the AI
            slide_id: The unique ID for this slide job
            user_id: The ID of the user creating the slides
            specialty: Optional medical specialty for this slide set
        """
        # Add metadata to each individual slide
        for index, slide in enumerate(slide_response.slides, start=1):
            slide.position = index
            slide.id = f"slide_{index:04d}"

        # Add overall metadata to the response object
        slide_response.slide_id = slide_id
        slide_response.slides_count = len(slide_response.slides)
        slide_response.status = "draft"
        slide_response.created_by = user_id
        slide_response.created_at = utc_now_iso_z()
        slide_response.updated_at = utc_now_iso_z()
        if specialty:
            slide_response.specialty = specialty

    def _save_to_firestore(self, slide_data: dict, app_type: str = "sca") -> tuple:
        """
        Save complete slide data to Firestore.

        Args:
            slide_data: Complete slide data dictionary
            app_type: Exam type (sca, plab, casc) - used for collection name

        Returns:
            tuple: (success: bool, firestore_doc_id: str or None)
        """
        try:
            slide_id = slide_data.get("slide_id")
            log.debug(f"[SLIDE_GENERATION] Saving slides to Firestore: {slide_id} (app_type: {app_type})")

            # Use app_type-specific collection name
            collection_name = COLLECTION_MAPPING[app_type]["slide"]

            # Add complete document to Firestore (auto-generates document ID)
            success, message = self.firestore_service.add_document(
                collection_name=collection_name,
                data=slide_data,
            )

            if not success:
                log.error(f"[SLIDE_GENERATION] Firestore save failed: {message}")
                return False, None

            # Extract the Firestore document ID from response
            firestore_doc_id = message.get("id") if isinstance(message, dict) else None

            if firestore_doc_id:
                log.debug(
                    f"[SLIDE_GENERATION] Successfully saved to Firestore with document ID: {firestore_doc_id}"
                )
                return True, firestore_doc_id
            else:
                log.error("[SLIDE_GENERATION] No document ID returned from Firestore")
                return False, None

        except Exception as e:
            log.error(
                f"[SLIDE_GENERATION] Exception during Firestore save: {str(e)}",
                exc_info=True,
            )
            return False, None

    def get_slides_by_id(self, slide_id: str, app_type: str = "sca") -> dict:
        """
        Retrieve slide data from Firestore by slide_id.

        Args:
            slide_id: The unique slide job ID
            app_type: Exam type (sca, plab, casc) - defaults to "sca"

        Returns:
            dict: Slide data or error message
        """
        if not self.firestore_service:
            return {"error": "Firestore service not configured"}, 500

        try:
            log.debug(f"[SLIDE_GENERATION] Retrieving slides: {slide_id} (app_type: {app_type})")

            # Get collection name for specific app_type
            collection_name = COLLECTION_MAPPING[app_type]["slide"]
            success, slides = self.firestore_service.get_documents(
                collection_name=collection_name, filters={"slide_id": slide_id}
            )

            if not success or not slides:
                log.error(f"[SLIDE_GENERATION] Slides not found: {slide_id} in {collection_name}")
                return {"error": "Slides not found"}, 404

            # Normalize the 'slides' field from a dict to a list if necessary
            self._normalize_slides_array(slides)

            log.debug(f"Found slides in {collection_name}")
            return slides, 200

        except Exception as e:
            log.error(f"[SLIDE_GENERATION] Failed to retrieve slides: {str(e)}", exc_info=True)
            return {"error": f"Failed to retrieve slides: {str(e)}"}, 500

    def update_slide(self, slide_id: str, updated_data: dict, app_type: str = "sca") -> dict:
        """
        Update slide content in Firestore (and JSON file if exists).

        Args:
            slide_id: The unique slide job ID
            updated_data: A dictionary containing fields to update.
                Example payload from the frontend:
                {
                    "topic": "New Topic Title",
                    "slides": [
                        {"title": "Updated Slide 1", ...},
                        {"title": "Updated Slide 2", ...}
                    ]
                }

            app_type: Exam type (sca, plab, casc) - defaults to "sca"

        Returns:
            dict: Success message or error
        """
        if not self.firestore_service:
            return {"error": "Firestore service not configured"}, 500

        try:
            log.debug(f"[SLIDE_UPDATE] Updating slide: {slide_id} (app_type: {app_type})")
            log.debug(f"[SLIDE_UPDATE] Updated data keys: {list(updated_data.keys())}")

            # Get collection name for specific app_type
            collection_name = COLLECTION_MAPPING[app_type]["slide"]

            # Get the current slide data from Firestore
            success, slide_data = self.firestore_service.get_documents(
                collection_name=collection_name, filters={"slide_id": slide_id}
            )

            if not success or not slide_data:
                log.error(f"[SLIDE_UPDATE] Slide not found in Firestore: {slide_id}")
                return {"error": "Slide not found"}, 404

            # Get the Firestore document ID
            firestore_doc_id = slide_data.get("id")
            if not firestore_doc_id:
                log.error(f"[SLIDE_UPDATE] No Firestore document ID found for: {slide_id}")
                return {"error": "Firestore document ID not found"}, 404

            # Update the slide data with new values using dot notation
            for key, value in updated_data.items():
                log.debug(f"Setting {key} = {str(value)[:100]}")
                set_nested_value(slide_data, key, value)

            # Update in Firestore
            # For Firestore, we need to send the full updated document
            success, message = self.firestore_service.update_document(
                collection_name=collection_name,
                document_id=firestore_doc_id,
                updated_data=slide_data,
            )

            if not success:
                log.error(f"Firestore update failed: {message}")
                return {"error": f"Firestore update failed: {message}"}, 500

            log.debug(f"[SLIDE_UPDATE] Updated Firestore document: {firestore_doc_id}")

            # Optionally update JSON file if it exists (not required)
            try:
                json_files = list(self.slides_base_dir.glob(f"**/slides_{slide_id}.json"))
                if json_files:
                    json_path = json_files[0]
                    with open(json_path, "w", encoding="utf-8") as handle:
                        json.dump(slide_data, handle, indent=2, ensure_ascii=False)
                    log.debug(f"[SLIDE_UPDATE] Also updated JSON file: {json_path}")
                else:
                    log.debug(f"[SLIDE_UPDATE] No JSON file found for {slide_id}, skipping JSON update")
            except Exception as json_error:
                log.warning(f"[SLIDE_UPDATE] Failed to update JSON file: {str(json_error)}")
                # Continue anyway since Firestore update succeeded

            return {"message": "Slide updated successfully", "slide_id": slide_id}, 200

        except Exception as e:
            log.error(f"[SLIDE_UPDATE] Failed to update slide: {str(e)}", exc_info=True)
            return {"error": f"Failed to update slide: {str(e)}"}, 500

    def update_slide_status(
        self,
        slide_id: str,
        status: str,
        additional_data: dict = None,
        app_type: str = None,
    ) -> dict:
        """
        Update the status of a slide generation job in Firestore.
        Fetches the document ID directly from Firestore.

        Args:
            slide_id: The unique slide job ID
            status: New status ("draft", "generating_audio", "generating_video", "completed", "failed")
            additional_data: Optional additional fields to update (e.g., audio_url, video_url)
            app_type: Optional app_type override (if not provided, will search all collections)

        Returns:
            dict: Success message or error
        """
        if not self.firestore_service:
            return {"error": "Firestore service not configured"}, 500

        try:
            log.debug(f"[SLIDE_GENERATION] Updating slide status: {slide_id} -> {status}")

            # Try all app_types to find the slide and get document ID
            firestore_doc_id = None
            detected_app_type = app_type

            for current_app_type in ["sca", "plab", "casc"]:
                if app_type and current_app_type != app_type:
                    continue  # Skip if specific app_type was provided

                collection_name = COLLECTION_MAPPING[current_app_type]["slide"]
                success, documents_result = self.firestore_service.get_documents(
                    collection_name=collection_name, filters={"slide_id": slide_id}
                )
                if success and documents_result:
                    firestore_doc_id = documents_result.get("id")
                    detected_app_type = current_app_type
                    log.debug(
                        f"[SLIDE_GENERATION] Found slide in {collection_name}, doc_id: {firestore_doc_id}"
                    )
                    break

            if not firestore_doc_id:
                log.error(f"[SLIDE_GENERATION] Slide not found in Firestore: {slide_id}")
                return {"error": "Slide not found in Firestore"}, 404

            update_data = {
                "status": status,
                "updated_at": utc_now_iso_z(),
            }

            if additional_data:
                update_data.update(additional_data)

            collection_name = COLLECTION_MAPPING[detected_app_type]["slide"]
            success, message = self.firestore_service.update_document(
                collection_name=collection_name,
                document_id=firestore_doc_id,
                updated_data=update_data,
            )

            if not success:
                log.error(f"Status update failed: {message}")
                return {"error": message}, 500

            log.debug(f"[SLIDE_GENERATION] Status updated successfully to: {status}")
            return {
                "message": "Status updated successfully",
                "slide_id": slide_id,
                "status": status,
            }, 200

        except Exception as e:
            log.error(f"[SLIDE_GENERATION] Failed to update status: {str(e)}", exc_info=True)
            return {"error": f"Failed to update status: {str(e)}"}, 500

    def _load_slide_data(self, slide_id: str, json_path: str = None) -> tuple[dict | None, str | None]:
        """
        Load slide data, prioritizing Firestore and falling back to a local JSON file.
        Also normalizes the 'slides' array from a dict to a list.

        Args:
            slide_id: The unique slide job ID.
            json_path: Optional path to the local JSON file.

        Returns:
            A tuple containing the slide_data (or None) and the app_type (or None).
        """
        log.debug(f"Loading slide data for: {slide_id}")
        slide_data = None
        app_type = None

        # Prioritize loading from Firestore if the service is available
        if self.firestore_service:
            for current_app_type in ["sca", "plab", "casc"]:
                collection_name = COLLECTION_MAPPING[current_app_type]["slide"]
                success, documents_result = self.firestore_service.get_documents(
                    collection_name=collection_name, filters={"slide_id": slide_id}
                )
                if success and documents_result:
                    slide_data = documents_result
                    app_type = current_app_type
                    log.debug(
                        "[SLIDE_DATA] Found and loaded slide data from Firestore "
                        f"collection: {collection_name}"
                    )
                    break

        # Fallback to loading from JSON if Firestore fails or is unavailable
        if not slide_data and json_path:
            log.warning(
                f"[SLIDE_DATA] Could not find slide in Firestore, falling back to JSON path: {json_path}"
            )
            json_path_obj = Path(json_path)
            if json_path_obj.exists():
                with open(json_path_obj, encoding="utf-8") as handle:
                    slide_data = json.load(handle)
                    app_type = slide_data.get("app_type", "sca")  # Get app_type from data or default
                log.debug("[SLIDE_DATA] Successfully loaded slide data from JSON file.")

        # If data was loaded, normalize the slides array
        if slide_data:
            self._normalize_slides_array(slide_data)

        return slide_data, app_type

    def delete_slide(self, slide_id: str, app_type: str = "sca") -> dict:
        """
        Delete a slide from Firestore and the local filesystem.

        This function attempts to delete the slide from both locations. It identifies
        the Firestore document by querying for the slide_id and the local files
        by searching for the slide's folder. The operation is successful if either
        the database record or the local folder is deleted.

        Args:
            slide_id: The unique slide job ID
            app_type: Exam type (sca, plab, casc) - defaults to "sca"

        Returns:
            dict: Success message or error
        """
        if not self.firestore_service:
            return {"error": "Firestore service not configured"}, 500

        try:
            log.debug(f"[SLIDE_DELETE] Deleting slide: {slide_id} (app_type: {app_type})")

            was_deleted = False

            # --- Step 1: Delete from Firestore ---
            collection_name = COLLECTION_MAPPING[app_type]["slide"]
            success, slide_doc = self.firestore_service.get_documents(
                collection_name=collection_name, filters={"slide_id": slide_id}
            )

            if success and slide_doc:
                firestore_doc_id = slide_doc.get("id")
                if firestore_doc_id:
                    del_success, message = self.firestore_service.delete_document(
                        collection_name=collection_name, document_id=firestore_doc_id
                    )
                    if del_success:
                        log.debug(f"[SLIDE_DELETE] Removed Firestore document: {firestore_doc_id}")
                        was_deleted = True
                    else:
                        log.warning(f"[SLIDE_DELETE] Firestore delete failed: {message}")
                else:
                    log.warning(f"[SLIDE_DELETE] Found doc in Firestore but it has no ID: {slide_id}")
            else:
                log.debug(f"[SLIDE_DELETE] Slide not found in Firestore collection '{collection_name}'")

            # --- Step 2: Delete from local filesystem ---
            json_files = list(self.slides_base_dir.glob(f"**/slides_{slide_id}.json"))
            if json_files:
                topic_folder = json_files[0].parent
                if topic_folder.exists():
                    import shutil

                    shutil.rmtree(topic_folder)
                    log.debug(f"[SLIDE_DELETE] Deleted local folder: {topic_folder}")
                    was_deleted = True
            else:
                log.debug(f"[SLIDE_DELETE] No local folder found for {slide_id}, skipping local delete.")

            # --- Step 3: Return result ---
            if was_deleted:
                return {
                    "message": "Slide deleted successfully",
                    "slide_id": slide_id,
                }, 200
            else:
                log.error(f"[SLIDE_DELETE] Slide not found anywhere for ID: {slide_id}")
                return {"error": "Slide not found"}, 404

        except Exception as e:
            log.error(f"[SLIDE_DELETE] Failed to delete slide: {str(e)}", exc_info=True)
            return {"error": f"Failed to delete slide: {str(e)}"}, 500

    def generate_audio_for_slides(self, slide_id: str, json_path: str = None) -> dict:
        """
        Generate audio narration for all slides using Cartesia TTS.
        For slides with bullets, generates separate audio segments per bullet for progressive reveal.
        For question slides (no bullets), adds a pause at the end.

        Args:
            slide_id: The slide job ID
            json_path: Optional path to JSON file (if not provided, will search in slides folder)

        Returns:
            dict: Result with audio file paths or error message
        """
        if not self.cartesia_client:
            return {"error": "Cartesia TTS not initialized - check API key"}, 500

        try:
            # Load slide data using the centralized method
            slide_data, app_type = self._load_slide_data(slide_id, json_path)

            if not slide_data:
                log.error(f"[AUDIO_GENERATION] Slide data not found for slide_id: {slide_id}")
                return {"error": f"Slide not found: {slide_id}"}, 404

            # Create or find topic folder for audio storage
            if not json_path:
                # Check if folder exists
                json_files = list(self.slides_base_dir.glob(f"**/slides_{slide_id}.json"))
                if json_files:
                    json_path = json_files[0]
                    topic_folder = json_path.parent
                else:
                    # Folder doesn't exist, so create it using the helper methods.
                    topic = slide_data.get("topic", "untitled_slides")
                    topic_folder = self._create_topic_folder(topic, slide_id)

                    # Save the JSON file in the newly created folder.
                    json_path = self._save_slides_json(slide_data, topic_folder, slide_id)

                    log.debug(f"[AUDIO_GENERATION] Created new topic folder and saved JSON: {topic_folder}")
            else:
                json_path = Path(json_path)
                topic_folder = json_path.parent

            audio_folder = topic_folder / "audio"
            audio_folder.mkdir(parents=True, exist_ok=True)

            log.debug(f"Using audio folder: {audio_folder}")

            slides = slide_data.get("slides", [])
            if not slides:
                return {"error": "No slides found in JSON"}, 400

            log.debug(f"[AUDIO_GENERATION] Generating audio for {len(slides)} slides (with bullet timing)")

            audio_paths = []
            total_duration = 0.0

            for slide_index, slide in enumerate(slides):
                slide_position = slide.get(
                    "position",
                )
                speaker_notes = slide.get("speaker_notes", "")
                bullets = slide.get("bullets", [])

                if not speaker_notes:
                    log.warning(f"[AUDIO_GENERATION] Slide {slide_position} has no speaker_notes, skipping")
                    continue

                # Question slides have speaker notes and no bullets.
                is_question_slide = speaker_notes and not bullets

                if is_question_slide:
                    updated_slide, slide_duration, new_audio_paths = self._process_question_slide_audio(
                        slide, audio_folder
                    )
                elif bullets:
                    updated_slide, slide_duration, new_audio_paths = self._process_bullet_slide_audio(
                        slide, audio_folder
                    )
                else:
                    updated_slide, slide_duration, new_audio_paths = self._process_regular_slide_audio(
                        slide, audio_folder
                    )

                # Update the slide in the main data structure
                slides[slide_index] = updated_slide
                total_duration += slide_duration
                audio_paths.extend(new_audio_paths)

            # Update JSON with audio info
            slide_data["total_duration"] = total_duration
            slide_data["status"] = "audio_generated"
            slide_data["updated_at"] = utc_now_iso_z()

            with open(json_path, "w", encoding="utf-8") as handle:
                json.dump(slide_data, handle, indent=2, ensure_ascii=False)

            log.debug(
                "[AUDIO_GENERATION] Audio generation completed: "
                f"{len(audio_paths)} files, {total_duration:.2f}s total"
            )

            # Update Firestore with complete slide data (including updated slides with audio metadata)
            if self.firestore_service:
                # Get the Firestore document ID
                success, firestore_doc = self.firestore_service.get_documents(
                    collection_name=COLLECTION_MAPPING[app_type]["slide"],
                    filters={"slide_id": slide_id},
                )

                if success and firestore_doc:
                    firestore_doc_id = firestore_doc.get("id")
                    if firestore_doc_id:
                        # Update Firestore with complete slide data including audio metadata
                        success, message = self.firestore_service.update_document(
                            collection_name=COLLECTION_MAPPING[app_type]["slide"],
                            document_id=firestore_doc_id,
                            updated_data=slide_data,
                        )
                        if success:
                            log.debug("[AUDIO_GENERATION] Updated Firestore with complete slide data")
                        else:
                            log.warning(f"[AUDIO_GENERATION] Failed to update Firestore: {message}")

            return {
                "message": "Audio generated successfully with bullet timing",
                "slide_id": slide_id,
                "audio_files_count": len(audio_paths),
                "total_duration": total_duration,
                "audio_folder": str(audio_folder),
                "audio_paths": audio_paths,
            }, 200

        except Exception as e:
            log.error(f"[AUDIO_GENERATION] Failed to generate audio: {str(e)}", exc_info=True)
            return {"error": f"Audio generation failed: {str(e)}"}, 500

    def _process_regular_slide_audio(self, slide: dict, audio_folder: Path) -> tuple[dict, float, list]:
        """
        Generates a single audio clip for a regular slide.

        Args:
            slide: The slide data dictionary.
            audio_folder: The path to the folder where audio will be saved.

        Returns:
            A tuple containing the updated slide data, the total duration for this slide,
            and a list of audio file paths created.
        """
        slide_position = slide.get("position")
        speaker_notes = slide.get("speaker_notes", "")
        audio_paths = []

        log.debug(f"[AUDIO_GENERATION] Slide {slide_position}: REGULAR slide (no bullets)")
        audio_file = audio_folder / f"slide_{slide_position:04d}.wav"

        # Check if audio already exists
        if audio_file.exists():
            log.debug(f"[AUDIO_GENERATION] Slide {slide_position}: Using existing audio file")
            audio_clip = AudioFileClip(str(audio_file))
            audio_duration = audio_clip.duration
            audio_clip.close()
        else:
            audio_data = self.cartesia_client.tts.bytes(
                model_id=self.model_id,
                transcript=speaker_notes,
                voice_id=self.voice_id,
                output_format=self.output_format,
            )

            with open(audio_file, "wb") as handle:
                handle.write(audio_data)

            audio_clip = AudioFileClip(str(audio_file))
            audio_duration = audio_clip.duration
            audio_clip.close()

        slide["audio_url"] = str(audio_file)
        slide["audio_duration"] = audio_duration
        slide["has_pause"] = False

        audio_paths.append(str(audio_file))

        return slide, audio_duration, audio_paths

    def _process_bullet_slide_audio(self, slide: dict, audio_folder: Path) -> tuple[dict, float, list]:
        """
        Generates segmented audio for a slide with bullet points.

        Args:
            slide: The slide data dictionary.
            audio_folder: The path to the folder where audio will be saved.

        Returns:
            A tuple containing the updated slide data, the total duration for this slide,
            and a list of audio file paths created.
        """
        slide_position = slide.get("position")
        speaker_notes = slide.get("speaker_notes", "")
        bullets = slide.get("bullets", [])
        audio_paths = []
        slide_total_duration = 0.0

        # Check if bullets have sub-bullets
        has_subbullets = any(isinstance(bullet, dict) and bullet.get("sub_bullets") for bullet in bullets)

        if has_subbullets:
            log.debug(
                f"[AUDIO_GENERATION] Slide {slide_position}: BULLET slide with "
                f"SUB-BULLETS ({len(bullets)} main bullets)"
            )
            bullet_segments = self._split_speaker_notes_for_bullets_with_subbullets(speaker_notes, bullets)
        else:
            log.debug(f"[AUDIO_GENERATION] Slide {slide_position}: BULLET slide ({len(bullets)} bullets)")
            bullet_segments = self._split_speaker_notes_for_bullets(speaker_notes, len(bullets))

        if bullet_segments is None:
            log.debug(f"[AUDIO_GENERATION] Slide {slide_position}: Falling back to single audio")
            return self._process_regular_slide_audio(slide, audio_folder)

        bullet_audio_segments = []
        for bullet_idx, segment_text in enumerate(bullet_segments):
            if not segment_text or len(segment_text.strip()) < 5:
                log.warning(f"[AUDIO_GENERATION]   Bullet {bullet_idx + 1}: Skipping empty/invalid segment")
                continue

            audio_file = audio_folder / f"slide_{slide_position:04d}_bullet_{bullet_idx:02d}.wav"

            # Check if audio already exists
            if audio_file.exists():
                log.debug(f"[AUDIO_GENERATION]   Bullet {bullet_idx + 1}: Using existing audio file")
                audio_clip = AudioFileClip(str(audio_file))
                segment_duration = audio_clip.duration
                audio_clip.close()
            else:
                try:
                    audio_data = self.cartesia_client.tts.bytes(
                        model_id=self.model_id,
                        transcript=segment_text,
                        voice_id=self.voice_id,
                        output_format=self.output_format,
                    )
                except ValueError as e:
                    log.warning(
                        f"[AUDIO_GENERATION]   Bullet {bullet_idx + 1}: Cartesia error: {e}. Skipping."
                    )
                    continue

                with open(audio_file, "wb") as handle:
                    handle.write(audio_data)

                audio_clip = AudioFileClip(str(audio_file))
                segment_duration = audio_clip.duration
                audio_clip.close()

            bullet_audio_segments.append(
                BulletAudioSegment(
                    bullet_index=bullet_idx,
                    audio_path=str(audio_file),
                    duration=segment_duration,
                    start_time=slide_total_duration,
                    text=segment_text,
                )
            )
            slide_total_duration += segment_duration
            audio_paths.append(str(audio_file))
            log.debug(f"[AUDIO_GENERATION]   Bullet {bullet_idx + 1}: {segment_duration:.2f}s")

        slide["bullet_audio_segments"] = [seg.model_dump() for seg in bullet_audio_segments]
        slide["audio_duration"] = slide_total_duration
        slide["has_pause"] = False

        return slide, slide_total_duration, audio_paths

    def _process_question_slide_audio(self, slide: dict, audio_folder: Path) -> tuple[dict, float, list]:
        """
        Generates audio for a question slide and adds a pause.

        Args:
            slide: The slide data dictionary.
            audio_folder: The path to the folder where audio will be saved.

        Returns:
            A tuple containing the updated slide data, the total duration for this slide,
            and a list of audio file paths created.
        """
        slide_position = slide.get("position")
        speaker_notes = slide.get("speaker_notes", "")
        audio_paths = []

        log.debug(f"[AUDIO_GENERATION] Slide {slide_position}: QUESTION slide (with pause)")
        audio_file = audio_folder / f"slide_{slide_position:04d}.wav"

        # Check if audio already exists
        if audio_file.exists():
            log.debug(f"[AUDIO_GENERATION] Slide {slide_position}: Using existing audio file")
            audio_clip = AudioFileClip(str(audio_file))
            audio_duration = audio_clip.duration
            audio_clip.close()
        else:
            audio_data = self.cartesia_client.tts.bytes(
                model_id=self.model_id,
                transcript=speaker_notes,
                voice_id=self.voice_id,
                output_format=self.output_format,
            )

            with open(audio_file, "wb") as handle:
                handle.write(audio_data)

            audio_clip = AudioFileClip(str(audio_file))
            audio_duration = audio_clip.duration
            audio_clip.close()

        pause_duration = 3.5  # 3.5 second pause for thinking

        slide["audio_url"] = str(audio_file)
        slide["audio_duration"] = audio_duration
        slide["has_pause"] = True
        slide["pause_duration"] = pause_duration

        total_slide_duration = audio_duration + pause_duration
        audio_paths.append(str(audio_file))

        log.debug(f"[AUDIO_GENERATION] Question slide: {audio_duration:.2f}s + {pause_duration}s pause")

        return slide, total_slide_duration, audio_paths

    def _apply_highlights_to_text(self, text: str, highlights: list) -> str:
        """
        Apply visual emphasis to highlighted terms in text by making them uppercase.

        Args:
            text: Original text
            highlights: List of terms to highlight (can be strings, dicts, or nested structures)

        Returns:
            str: Text with highlights emphasized
        """
        if not highlights:
            return text

        result = text

        # Flatten and normalize highlights to a list of strings
        normalized_highlights = []

        for highlight in highlights:
            if highlight is None:
                continue

            # Handle dict format
            if isinstance(highlight, dict):
                # Try common dict keys
                highlight_text = highlight.get("text") or highlight.get("term") or highlight.get("value")
                if highlight_text:
                    normalized_highlights.append(str(highlight_text))
            # Handle list format (nested lists)
            elif isinstance(highlight, list):
                # Recursively process nested lists
                for item in highlight:
                    if isinstance(item, dict):
                        item_text = item.get("text") or item.get("term") or item.get("value")
                        if item_text:
                            normalized_highlights.append(str(item_text))
                    elif isinstance(item, str) and item.strip():
                        normalized_highlights.append(item)
            # Handle string format
            elif isinstance(highlight, str) and highlight.strip():
                normalized_highlights.append(highlight)

        # Apply highlights
        for highlight_text in normalized_highlights:
            try:
                # Case-insensitive replacement, make highlighted terms uppercase
                pattern = re.compile(re.escape(highlight_text), re.IGNORECASE)
                result = pattern.sub(highlight_text.upper(), result)
            except Exception as e:
                log.warning(f"[HIGHLIGHT] Failed to apply highlight '{highlight_text}': {str(e)}")
                continue

        return result

    def _split_speaker_notes_for_bullets(self, speaker_notes: str, num_bullets: int) -> list:
        """
        Split speaker notes into segments for each bullet point.
        Uses sentence-based splitting for natural audio segmentation.

        Args:
            speaker_notes: Full speaker notes text
            num_bullets: Number of bullets to create segments for

        Returns:
            list: List of text segments, one per bullet, or None if not enough content
        """
        # Split by sentences (. ! ?)
        sentences = re.split(r"(?<=[.!?])\s+", speaker_notes.strip())

        # Filter out empty sentences
        sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

        # If we don't have enough sentences, return None to indicate single audio should be used
        # Use 50% threshold - only fall back to single audio if we have less than half the bullets
        if len(sentences) < num_bullets * 0.5:
            log.warning(
                f"[AUDIO_SPLIT] Not enough sentences ({len(sentences)}) for "
                f"{num_bullets} bullets. Using single audio."
            )
            return None

        if len(sentences) == 0:
            return None
        else:
            # Distribute sentences across bullets more evenly
            segments = []
            sentences_per_bullet = len(sentences) / num_bullets

            current_segment = []
            target_sentences = sentences_per_bullet

            for sentence_index, sentence in enumerate(sentences):
                current_segment.append(sentence)

                # Check if we should close this segment
                if len(current_segment) >= target_sentences and len(segments) < num_bullets - 1:
                    segments.append(" ".join(current_segment))
                    current_segment = []
                    target_sentences = (len(sentences) - sentence_index - 1) / (num_bullets - len(segments))

            # Add remaining sentences to last segment
            if current_segment:
                segments.append(" ".join(current_segment))

        # Final validation - ensure no empty segments
        segments = [seg for seg in segments if seg and seg.strip() not in ["", ".", ",", "!"]]

        # If we lost too many segments, return None to use single audio
        if len(segments) < num_bullets * 0.5:
            log.warning("[AUDIO_SPLIT] Too many empty segments. Using single audio.")
            return None

        # Trim to exact number of bullets (shouldn't happen with proper distribution)
        return segments[:num_bullets]

    def _resolve_image_path(self, image_url: str, topic_folder: Path) -> Path:
        """Resolve an image path from a slide's ``image_url``.

        Security (SEC-018): ``image_urls`` are LLM-generated, so the value is
        untrusted. Reject absolute paths and any ``..`` traversal, and confirm
        the resolved path stays inside its base directory, so a crafted url
        such as ``"../../../../etc/passwd"`` cannot escape the slides tree and
        be embedded into the rendered (and later S3-uploaded) video. An unsafe
        url resolves to a path that does not exist, so every caller's existing
        ``image_path.exists()`` guard simply skips it.
        """
        base = self.slides_base_dir if image_url.startswith("images/") else topic_folder

        candidate = Path(image_url)
        if candidate.is_absolute() or ".." in candidate.parts:
            log.warning(f"Rejected unsafe image path (traversal/absolute): {image_url!r}")
            return base / "__rejected_unsafe_image_path__"

        image_path = (base / candidate).resolve()
        try:
            image_path.relative_to(base.resolve())
        except ValueError:
            log.warning(f"Rejected out-of-tree image path: {image_url!r}")
            return base / "__rejected_unsafe_image_path__"

        if not image_path.exists():
            log.warning(f"Image not found: {image_path}")
        return image_path

    def _create_image_clips(
        self,
        slide: dict,
        topic_folder: Path,
        total_duration: float,
        width: int,
        height: int,
        side_padding: int,
        content_y: int,
    ) -> tuple:
        """Creates image clips for a slide and returns clips and layout adjustments."""
        image_urls = slide.get("image_urls")
        content_width = width - (2 * side_padding)
        is_full_image = False
        elements = []

        if not image_urls:
            return elements, side_padding, content_width, is_full_image

        layout = slide.get("layout", "text_image_right")

        if layout == "triple_image" and len(image_urls) == 3:
            is_full_image = True
            img_width = int(width * 0.3)
            spacing = (width - (3 * img_width)) / 4
            positions = [spacing, spacing * 2 + img_width, spacing * 3 + img_width * 2]
            for image_index, url in enumerate(image_urls):
                image_path = self._resolve_image_path(url, topic_folder)
                if image_path.exists():
                    elements.append(
                        ImageClip(str(image_path))
                        .with_duration(total_duration)
                        .resized(width=img_width)
                        .with_position((positions[image_index], "center"))
                    )
        else:
            image_path = self._resolve_image_path(image_urls[0], topic_folder)
            if image_path.exists():
                if layout == "full_image":
                    is_full_image = True
                    image_clip = ImageClip(str(image_path)).with_duration(total_duration)
                    max_width, max_height = int(width * 0.6), int(height * 0.6)
                    image_clip = (
                        image_clip.resized(height=max_height)
                        if image_clip.h > image_clip.w
                        else image_clip.resized(width=max_width)
                    )
                    elements.append(image_clip.with_position("center"))
                elif layout == "text_image_left":
                    elements.append(
                        ImageClip(str(image_path))
                        .with_duration(total_duration)
                        .resized(width=int(width * 0.4))
                        .with_position((50, content_y))
                    )
                    side_padding = 50 + int(width * 0.4) + 80
                    content_width = width - side_padding - 50
                elif layout == "text_image_right":
                    elements.append(
                        ImageClip(str(image_path))
                        .with_duration(total_duration)
                        .resized(width=int(width * 0.4))
                        .with_position((width - int(width * 0.4) - 50, content_y))
                    )
                    content_width = width - side_padding - int(width * 0.4) - 80 - 50

        return elements, side_padding, content_width, is_full_image

    def upload_video_to_s3(self, video_path: Path, slide_id: str, topic: str, app_type: str = "sca") -> dict:
        """
        Upload the generated video to AWS S3.

        Args:
            video_path: Path to the generated video file
            slide_id: The slide job ID
            topic: The slide topic/name
            app_type: Exam type (sca, plab, casc) - used for S3 folder

        Returns:
            dict: Result with S3 URL or error message
        """
        try:
            # Format the S3 file name with app_type-specific folder
            formatted_topic = topic.lower().replace(" ", "_")[:50]
            s3_key = f"{self.s3_base_folder}/{app_type}/{formatted_topic}_{slide_id}.mp4"

            # Upload to S3
            log.debug(f"Uploading video to S3: {s3_key}")
            with open(video_path, "rb") as file:
                self.s3_client.upload_fileobj(
                    file,
                    self._s3_bucket,
                    s3_key,
                    ExtraArgs={"ContentType": "video/mp4"},
                )

            # Generate the public URL
            video_url = f"https://{self._s3_bucket}.s3.{self._aws_region}.amazonaws.com/{s3_key}"
            log.debug(f"Video uploaded successfully: {video_url}")

            return {"success": True, "video_url": video_url}

        except Exception as e:
            error_msg = f"Failed to upload video to S3: {str(e)}"
            log.error(f"{error_msg}", exc_info=True)
            return {"success": False, "error": error_msg}

    def create_video_from_slides(self, slide_id: str, json_path: str = None) -> dict:
        """
        Create a continuous video from all slides using MoviePy.

        Args:
            slide_id: The slide job ID
            json_path: Optional path to JSON file

        Returns:
            dict: Result with video file path or error message
        """
        try:
            # Find or create local folder for audio files
            if not json_path:
                json_files = list(self.slides_base_dir.glob(f"**/slides_{slide_id}.json"))
                if json_files:
                    json_path = json_files[0]
                    topic_folder = Path(json_path).parent
                else:
                    # Folder doesn't exist yet - this means audio generation created it
                    # Just find any folder with this slide_id pattern
                    json_files = list(self.slides_base_dir.glob(f"**/{slide_id}"))
                    if not json_files:
                        return {
                            "error": (
                                f"Slides folder not found for slide_id: {slide_id}. Generate audio first."
                            )
                        }, 404
                    topic_folder = json_files[0]
                    json_path = topic_folder / f"slides_{slide_id}.json"
                    log.debug(f"[VIDEO_GENERATION] Using topic folder: {topic_folder}")
            else:
                json_path = Path(json_path)
                topic_folder = json_path.parent

            log.debug(f"Using topic folder: {topic_folder}")

            # Load slide data using the centralized method
            slide_data, app_type = self._load_slide_data(slide_id, json_path)

            if not slide_data:
                log.error(f"[VIDEO_GENERATION] Slide data not found for slide_id: {slide_id}")
                return {"error": f"Slide not found: {slide_id}"}, 404

            slides = slide_data.get("slides", [])
            if not slides:
                return {"error": "No slides found"}, 400

            # Check if audio files exist
            audio_folder = topic_folder / "audio"
            if not audio_folder.exists():
                return {"error": "Audio files not found. Generate audio first."}, 400

            log.debug(f"[VIDEO_GENERATION] Creating video for all {len(slides)} slides")

            # Generate video clips for each slide
            video_clips = []
            total_duration = 0.0

            for slide_number, slide in enumerate(slides, 1):
                log.debug(f"[VIDEO_GENERATION] Creating video for slide {slide_number}/{len(slides)}")

                clip = self._create_slide_clip(slide, topic_folder)
                if clip:
                    video_clips.append(clip)
                    total_duration += clip.duration
                else:
                    log.warning(f"[VIDEO_GENERATION] Failed to create clip for slide {slide_number}")

            if not video_clips:
                return {"error": "Failed to create any video clips"}, 500

            # Add branded end screen with logo
            end_screen_duration = 3.0  # 3 seconds
            width, height = 1920, 1080

            end_screen = self._create_end_screen(end_screen_duration, width, height)
            video_clips.append(end_screen)

            # Concatenate all clips into one continuous auto-playing video
            log.debug(f"[VIDEO_GENERATION] Concatenating {len(video_clips)} clips (all slides + end screen)")
            final_video = concatenate_videoclips(video_clips, method="compose")

            # Save final video
            video_filename = f"teaching_video_{slide_id}.mp4"
            video_path = topic_folder / video_filename

            log.debug(f"[VIDEO_GENERATION] Rendering final video to: {video_path}")
            final_video.write_videofile(
                str(video_path),
                fps=24,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=str(topic_folder / "temp-audio.m4a"),
                remove_temp=True,
                threads=4,
                preset="medium",
            )

            # Close clips to free memory
            final_video.close()
            for clip in video_clips:
                clip.close()

            log.debug(f"[VIDEO_GENERATION] Video generation completed: {video_path}")

            # Upload video to S3
            topic = slide_data.get("topic", "untitled")
            app_type = app_type or slide_data.get("app_type", "sca")  # Use detected app_type
            upload_result = self.upload_video_to_s3(video_path, slide_id, topic, app_type)

            if not upload_result["success"]:
                log.warning(f"[VIDEO_GENERATION] Failed to upload video to S3: {upload_result.get('error')}")
                video_url = str(video_path)  # Fallback to local path
            else:
                video_url = upload_result["video_url"]
                log.debug(f"[VIDEO_GENERATION] Video uploaded to S3: {video_url}")

            # Update JSON with video info
            slide_data["final_video_url"] = video_url
            slide_data["local_video_path"] = str(video_path)
            slide_data["total_duration"] = total_duration
            slide_data["status"] = "completed"
            slide_data["updated_at"] = utc_now_iso_z()

            with open(json_path, "w", encoding="utf-8") as handle:
                json.dump(slide_data, handle, indent=2, ensure_ascii=False)

            # Update Firestore status with S3 URL
            if self.firestore_service:
                self.update_slide_status(
                    slide_id,
                    "completed",
                    {
                        "final_video_url": video_url,
                        "local_video_path": str(video_path),
                        "total_duration": total_duration,
                    },
                    app_type=app_type,  # Pass app_type to ensure it updates the correct collection
                )

            return {
                "message": "Video generated and uploaded successfully",
                "slide_id": slide_id,
                "video_path": str(video_path),
                "video_url": video_url,
                "total_duration": total_duration,
                "slides_count": len(slides),
            }, 200

        except Exception as e:
            log.error(f"[VIDEO_GENERATION] Failed to generate video: {str(e)}", exc_info=True)
            return {"error": f"Video generation failed: {str(e)}"}, 500

    def _create_end_screen(self, duration: float, width: int, height: int) -> CompositeVideoClip:
        """
        Creates a branded end screen for the video.

        Args:
            duration: The duration of the end screen.
            width: The width of the video.
            height: The height of the video.

        Returns:
            A CompositeVideoClip representing the end screen.
        """
        # Create end screen background
        end_background = ColorClip(
            size=(width, height),
            color=(245, 245, 247),
            duration=duration,
        )
        elements = [end_background]

        # Check if logo exists and add it, otherwise add text
        logo_path = self.slides_base_dir / "images" / "logo.png"
        if logo_path.exists():
            logo_clip = (
                ImageClip(str(logo_path)).with_duration(duration).resized(width=400).with_position("center")
            )
            elements.append(logo_clip)
            log.debug("Added logo to end screen")
        else:
            end_text = (
                TextClip(
                    text="OSCE Guide",
                    font_size=72,
                    color="#000000",
                    font=str(self.font_path),
                    stroke_color="#000000",
                    stroke_width=2,
                    size=(800, 200),
                )
                .with_duration(duration)
                .with_position("center")
            )
            elements.append(end_text)
            log.debug("[VIDEO_GENERATION] Added text to end screen (no logo found)")

        return CompositeVideoClip(elements)

    def _create_progressive_bullet_clip(
        self,
        slide: dict,
        topic_folder: Path,
        width: int,
        height: int,
        side_padding: int,
        content_width: int,
        content_width_chars: int,
        title_y: int,
        content_y: int,
    ) -> CompositeVideoClip:
        """
        Create a video clip with progressive bullet reveals.
        Each bullet appears as its audio segment plays.

            Args:
            slide: Slide data dictionary
            topic_folder: Path to topic folder
            width, height: Video dimensions
            side_padding, content_width, content_width_chars: Layout parameters
            title_y, content_y: Vertical positions

            Returns:
            CompositeVideoClip: Video clip with progressive bullet reveals
        """
        try:
            bullet_segments = slide["bullet_audio_segments"]
            bullets = slide.get("bullets", [])
            total_duration = slide["audio_duration"]

            log.debug(f"[VIDEO_GENERATION] Creating progressive bullet reveal for {len(bullets)} bullets")

            image_elements, side_padding, content_width, is_full_image = self._create_image_clips(
                slide,
                topic_folder,
                total_duration,
                width,
                height,
                side_padding,
                content_y,
            )

            # Create background
            background_img_path = self.slides_base_dir / "images" / "bg.png"
            log.debug(f"[VIDEO_GENERATION] Checking background path: {background_img_path}")
            log.debug(f"[VIDEO_GENERATION] Background path exists: {background_img_path.exists()}")
            if not background_img_path.exists():
                background = ColorClip(size=(width, height), color=(245, 245, 247), duration=total_duration)
            else:
                background = ImageClip(str(background_img_path)).with_duration(total_duration)

            elements = [background]
            elements.extend(image_elements)

            # Title (visible entire time, with highlights applied as uppercase)
            if not is_full_image:
                title_text = slide["title"]

                # Ensure title_text is a string
                if not isinstance(title_text, str):
                    title_text = str(title_text) if title_text else ""

                highlights = slide.get("highlights", [])

                # Ensure highlights is a list
                if not isinstance(highlights, list):
                    highlights = []

                if highlights:
                    title_text = self._apply_highlights_to_text(title_text, highlights)

                title = (
                    TextClip(
                        text=title_text,
                        font_size=64,
                        color="#FF6262",
                        font=str(self.font_path),
                        stroke_color="#FF6262",
                        stroke_width=1,
                        text_align="center",
                        size=(content_width, 200),
                        method="caption",
                    )
                    .with_duration(total_duration)
                    .with_position(("center", title_y))
                    .with_effects([CrossFadeIn(0.3)])  # Simple fade-in
                )
                elements.append(title)

            # Create individual text clips for each bullet that appear at the right time
            bullet_y_spacing = 120  # Increased space between bullets to accommodate multi-line text

            # Get highlights for this slide (ensure it's a list)
            slide_highlights = slide.get("highlights", [])
            if not isinstance(slide_highlights, list):
                slide_highlights = []

            # First, recalculate actual start times based on real audio file durations
            actual_start_times = []
            cumulative_time = 0.0
            for segment in bullet_segments:
                audio_path = Path(segment["audio_path"])
                if audio_path.exists():
                    audio_clip = AudioFileClip(str(audio_path))
                    actual_duration = audio_clip.duration
                    actual_start_times.append(cumulative_time)
                    cumulative_time += actual_duration
                    audio_clip.close()
                else:
                    # Fallback to stored start_time if file doesn't exist
                    actual_start_times.append(segment.get("start_time", 0.0))

            for bullet_idx, bullet_text in enumerate(bullets):
                if bullet_idx >= len(bullet_segments):
                    break

                # Use actual start time from real audio durations
                start_time = (
                    actual_start_times[bullet_idx]
                    if bullet_idx < len(actual_start_times)
                    else bullet_segments[bullet_idx]["start_time"]
                )

                # Make bullet appear 0.2s BEFORE audio starts for better readability
                bullet_appear_time = max(0, start_time - 0.2)

                # Ensure bullet_text is a string
                if isinstance(bullet_text, dict):
                    bullet_text = bullet_text.get("text", "")

                if not isinstance(bullet_text, str):
                    bullet_text = str(bullet_text) if bullet_text else ""

                # Apply highlights to this bullet
                if slide_highlights:
                    bullet_text = self._apply_highlights_to_text(bullet_text, slide_highlights)

                # Add bullet point prefix
                formatted_bullet = f"• {bullet_text}"
                bullet_y = content_y + (bullet_idx * bullet_y_spacing)

                # Create slide-in animation from top for bullet
                slide_duration = 0.4  # Duration of slide-in animation
                start_y = bullet_y - 50  # Start 50px above final position
                end_y = bullet_y  # End at normal position

                def make_bullet_slide_position(start_y_val, end_y_val, x_val, slide_dur):
                    """Builds the per-frame position function MoviePy calls to animate one bullet
                    sliding in from above its final resting place.
                    """

                    def bullet_slide_in(elapsed_seconds):
                        """Slide in from top over 0.4 seconds, starting immediately when bullet appears.
                        `elapsed_seconds` is relative to clip start (0 when clip appears)."""
                        if elapsed_seconds < slide_dur:
                            # Slide from top to final position smoothly
                            progress = elapsed_seconds / slide_dur
                            # Use ease-out for smoother animation
                            eased_progress = 1 - (1 - progress) ** 2
                            current_y = start_y_val + (end_y_val - start_y_val) * eased_progress
                            return (x_val, current_y)
                        else:
                            # Stay at final position
                            return (x_val, end_y_val)

                    return bullet_slide_in

                bullet_clip = (
                    TextClip(
                        text=formatted_bullet,
                        font_size=40,
                        color="#1D1D1F",
                        font=str(self.font_path),
                        method="caption",
                        size=(content_width, 120),
                        horizontal_align="left",
                        vertical_align="top",
                    )
                    .with_start(bullet_appear_time)  # Appear 0.2s before audio
                    .with_duration(total_duration - bullet_appear_time)
                    .with_position(make_bullet_slide_position(start_y, end_y, side_padding, slide_duration))
                    .with_effects([CrossFadeIn(0.15)])  # Quick fade with slide
                )

                elements.append(bullet_clip)
                log.debug(
                    f"[VIDEO_GENERATION]   Bullet {bullet_idx + 1} appears at "
                    f"{bullet_appear_time:.2f}s (audio at {start_time:.2f}s)"
                )

            # Concatenate all audio segments
            audio_clips = []
            for segment in bullet_segments:
                audio_path = Path(segment["audio_path"])
                if audio_path.exists():
                    audio_clips.append(AudioFileClip(str(audio_path)))

            combined_audio = concatenate_audioclips(audio_clips) if audio_clips else None

            # Compose video
            composite = CompositeVideoClip(elements)

            # Add audio
            if combined_audio:
                composite = composite.with_audio(combined_audio)

            log.debug(f"[VIDEO_GENERATION] Progressive bullet clip created (duration: {total_duration:.2f}s)")

            return composite

        except Exception as e:
            log.error(
                f"[VIDEO_GENERATION] Error creating progressive bullet clip: {str(e)}",
                exc_info=True,
            )
            return None

    def _create_progressive_bullet_clip_with_subbullets(
        self,
        slide: dict,
        topic_folder: Path,
        width: int,
        height: int,
        side_padding: int,
        content_width: int,
        content_width_chars: int,
        title_y: int,
        content_y: int,
    ) -> CompositeVideoClip:
        """
        Create a video clip with progressive bullet reveals including sub-bullets.
        Sub-bullets appear indented and with proper spacing.

        Args:
            slide: Slide data dictionary
            topic_folder: Path to topic folder
            width, height: Video dimensions
            side_padding, content_width, content_width_chars: Layout parameters
            title_y, content_y: Vertical positions

        Returns:
            CompositeVideoClip: Video clip with progressive bullet and sub-bullet reveals
        """
        try:
            bullet_segments = slide["bullet_audio_segments"]
            bullets = slide.get("bullets", [])
            total_duration = slide["audio_duration"]

            log.debug(
                "[VIDEO_GENERATION] Creating progressive bullet reveal with "
                f"sub-bullets for {len(bullets)} bullets"
            )

            image_elements, side_padding, content_width, is_full_image = self._create_image_clips(
                slide,
                topic_folder,
                total_duration,
                width,
                height,
                side_padding,
                content_y,
            )

            # Create background
            background_img_path = self.slides_base_dir / "images" / "bg.png"
            if not background_img_path.exists():
                background = ColorClip(size=(width, height), color=(245, 245, 247), duration=total_duration)
            else:
                background = ImageClip(str(background_img_path)).with_duration(total_duration)

            elements = [background]
            elements.extend(image_elements)

            # Title (visible entire time, with highlights applied as uppercase)
            if not is_full_image:
                title_text = slide["title"]
                highlights = slide.get("highlights", [])
                if highlights:
                    title_text = self._apply_highlights_to_text(title_text, highlights)

                title = (
                    TextClip(
                        text=title_text,
                        font_size=64,
                        color="#FF6262",
                        font=str(self.font_path),
                        stroke_color="#FF6262",
                        stroke_width=1,
                        text_align="center",
                        size=(content_width, 200),
                        method="caption",
                    )
                    .with_duration(total_duration)
                    .with_position(("center", title_y))
                    .with_effects([CrossFadeIn(0.3)])  # Simple fade-in
                )
                elements.append(title)

            # Enhanced spacing calculations for bullets and sub-bullets
            main_bullet_font_size = 40
            sub_bullet_font_size = 34
            main_bullet_line_height = 50  # Base height for main bullets
            sub_bullet_line_height = 45  # Height for sub-bullets
            sub_bullet_indent = 60  # Indentation for sub-bullets

            # Get highlights for this slide (ensure it's a list)
            slide_highlights = slide.get("highlights", [])
            if not isinstance(slide_highlights, list):
                slide_highlights = []

            # First, recalculate actual start times based on real audio file durations
            actual_start_times = []
            cumulative_time = 0.0
            for segment in bullet_segments:
                audio_path = Path(segment["audio_path"])
                if audio_path.exists():
                    audio_clip = AudioFileClip(str(audio_path))
                    actual_duration = audio_clip.duration
                    actual_start_times.append(cumulative_time)
                    cumulative_time += actual_duration
                    audio_clip.close()
                else:
                    # Fallback to stored start_time if file doesn't exist
                    actual_start_times.append(segment.get("start_time", 0.0))

            current_y = content_y
            segment_index = 0

            for bullet_idx, bullet_data in enumerate(bullets):
                if segment_index >= len(bullet_segments):
                    break

                # Handle bullet data structure (could be string or dict)
                if isinstance(bullet_data, dict):
                    bullet_text = bullet_data.get("text", "")
                    sub_bullets = bullet_data.get("sub_bullets", [])
                    bullet_highlights = bullet_data.get("highlights", [])
                else:
                    # Legacy format: just a string
                    bullet_text = str(bullet_data)
                    sub_bullets = []
                    bullet_highlights = []

                # Ensure bullet_text is a string
                if not isinstance(bullet_text, str):
                    bullet_text = str(bullet_text) if bullet_text else ""

                # Ensure highlights are lists
                if not isinstance(bullet_highlights, list):
                    bullet_highlights = []

                # Safely combine slide-level and bullet-level highlights
                # Make a flat list of all highlights
                all_highlights = []

                # Add slide highlights
                if isinstance(slide_highlights, list):
                    all_highlights.extend(slide_highlights)

                # Add bullet highlights
                if isinstance(bullet_highlights, list):
                    all_highlights.extend(bullet_highlights)

                # Main bullet segment - use actual start time from real audio durations
                segment = bullet_segments[segment_index]
                start_time = (
                    actual_start_times[segment_index]
                    if segment_index < len(actual_start_times)
                    else segment["start_time"]
                )
                segment_index += 1

                # Make bullet appear 0.2s BEFORE audio starts for better readability
                bullet_appear_time = max(0, start_time - 0.2)

                # Apply highlights to main bullet
                if all_highlights:
                    bullet_text = self._apply_highlights_to_text(bullet_text, all_highlights)

                # Calculate dynamic height for main bullet based on text length
                estimated_lines = max(1, len(bullet_text) // 80)
                bullet_height = main_bullet_line_height * estimated_lines

                # Create main bullet clip with slide-in animation from top
                formatted_bullet = f"• {bullet_text}"

                # Create slide-in animation from top for bullet
                slide_duration = 0.4
                start_y = current_y - 50  # Start 50px above final position
                end_y = current_y  # End at normal position

                def make_bullet_slide_position(start_y_val, end_y_val, x_val, slide_dur):
                    """Builds the per-frame position function MoviePy calls to animate one bullet
                    sliding in from above its final resting place.
                    """

                    def bullet_slide_in(elapsed_seconds):
                        """Slide in from top over 0.4 seconds, starting immediately when bullet appears.
                        `elapsed_seconds` is relative to clip start (0 when clip appears)."""
                        if elapsed_seconds < slide_dur:
                            # Slide from top to final position smoothly
                            progress = elapsed_seconds / slide_dur
                            # Use ease-out for smoother animation
                            eased_progress = 1 - (1 - progress) ** 2
                            current_y_pos = start_y_val + (end_y_val - start_y_val) * eased_progress
                            return (x_val, current_y_pos)
                        else:
                            # Stay at final position
                            return (x_val, end_y_val)

                    return bullet_slide_in

                bullet_clip = (
                    TextClip(
                        text=formatted_bullet,
                        font_size=main_bullet_font_size,
                        color="#1D1D1F",
                        font=str(self.font_path),
                        method="caption",
                        size=(content_width - sub_bullet_indent, bullet_height),
                        horizontal_align="left",
                        vertical_align="top",
                    )
                    .with_start(bullet_appear_time)  # Appear 0.2s before audio
                    .with_duration(total_duration - bullet_appear_time)
                    .with_position(make_bullet_slide_position(start_y, end_y, side_padding, slide_duration))
                    .with_effects([CrossFadeIn(0.15)])  # Quick fade with slide
                )

                elements.append(bullet_clip)
                log.debug(
                    f"[VIDEO_GENERATION]   Main Bullet {bullet_idx + 1} appears at "
                    f"{bullet_appear_time:.2f}s (audio at {start_time:.2f}s), y={current_y}"
                )

                # Move down by the bullet height
                current_y += bullet_height

                # Process sub-bullets
                for sub_bullet_data in sub_bullets:
                    if segment_index >= len(bullet_segments):
                        break

                    # Handle sub-bullet data structure
                    if isinstance(sub_bullet_data, dict):
                        sub_bullet_text = sub_bullet_data.get("text", "")
                        sub_bullet_highlights = sub_bullet_data.get("highlights", [])
                    else:
                        sub_bullet_text = str(sub_bullet_data)
                        sub_bullet_highlights = []

                    # Ensure sub_bullet_text is a string
                    if not isinstance(sub_bullet_text, str):
                        sub_bullet_text = str(sub_bullet_text) if sub_bullet_text else ""

                    # Ensure sub_bullet_highlights is a list
                    if not isinstance(sub_bullet_highlights, list):
                        sub_bullet_highlights = []

                    # Combine all relevant highlights - use extend to avoid nesting
                    sub_all_highlights = []
                    sub_all_highlights.extend(all_highlights)
                    if isinstance(sub_bullet_highlights, list):
                        sub_all_highlights.extend(sub_bullet_highlights)

                    # Get audio segment for sub-bullet - use actual start time from real audio durations
                    sub_segment = bullet_segments[segment_index]
                    sub_start_time = (
                        actual_start_times[segment_index]
                        if segment_index < len(actual_start_times)
                        else sub_segment["start_time"]
                    )
                    segment_index += 1

                    # Make sub-bullet appear 0.2s BEFORE audio starts
                    sub_bullet_appear_time = max(0, sub_start_time - 0.2)

                    # Apply highlights to sub-bullet
                    if sub_all_highlights:
                        sub_bullet_text = self._apply_highlights_to_text(sub_bullet_text, sub_all_highlights)

                    # Calculate dynamic height for sub-bullet
                    estimated_sub_lines = max(1, len(sub_bullet_text) // 85)
                    sub_bullet_height = sub_bullet_line_height * estimated_sub_lines

                    # Create sub-bullet clip (indented with simple dash) - no slide-in, just fade
                    formatted_sub_bullet = f"- {sub_bullet_text}"
                    sub_bullet_clip = (
                        TextClip(
                            text=formatted_sub_bullet,
                            font_size=sub_bullet_font_size,
                            color="#4A4A4A",  # Slightly lighter color for sub-bullets
                            font=str(self.font_path),
                            method="caption",
                            size=(
                                content_width - sub_bullet_indent * 2,
                                sub_bullet_height,
                            ),
                            horizontal_align="left",
                            vertical_align="top",
                        )
                        .with_start(sub_bullet_appear_time)  # Appear 0.2s before audio
                        .with_duration(total_duration - sub_bullet_appear_time)
                        .with_position((side_padding + sub_bullet_indent, current_y))
                        .with_effects([CrossFadeIn(0.2)])  # Just fade-in, no slide
                    )

                    elements.append(sub_bullet_clip)
                    log.debug(
                        f"[VIDEO_GENERATION]     Sub-Bullet appears at "
                        f"{sub_bullet_appear_time:.2f}s (audio at {sub_start_time:.2f}s), "
                        f"y={current_y}"
                    )

                    # Move down by the sub-bullet height
                    current_y += sub_bullet_height

                # Add small spacing after each main bullet group
                current_y += 10

            # Concatenate all audio segments
            audio_clips = []
            for segment in bullet_segments:
                audio_path = Path(segment["audio_path"])
                if audio_path.exists():
                    audio_clips.append(AudioFileClip(str(audio_path)))

            combined_audio = concatenate_audioclips(audio_clips) if audio_clips else None

            # Compose video
            composite = CompositeVideoClip(elements)

            # Add audio
            if combined_audio:
                composite = composite.with_audio(combined_audio)

            log.debug(
                "[VIDEO_GENERATION] Progressive bullet clip with sub-bullets created "
                f"(duration: {total_duration:.2f}s)"
            )

            return composite

        except Exception as e:
            log.error(
                f"[VIDEO_GENERATION] Error creating progressive bullet clip with sub-bullets: {str(e)}",
                exc_info=True,
            )
            return None

    # Enhanced audio splitting for sub-bullets

    def _split_speaker_notes_for_bullets_with_subbullets(self, speaker_notes: str, bullets: list) -> list:
        """
        Split speaker notes into segments for each bullet and sub-bullet.

        Args:
            speaker_notes: Full speaker notes text
            bullets: List of bullet dictionaries with sub_bullets

        Returns:
            list: List of text segments, one per bullet/sub-bullet
        """
        # Count total items (main bullets + sub-bullets)
        total_items = 0
        for bullet in bullets:
            total_items += 1  # Main bullet
            if isinstance(bullet, dict):
                total_items += len(bullet.get("sub_bullets", []))

        # Split by sentences
        sentences = re.split(r"(?<=[.!?])\s+", speaker_notes.strip())
        sentences = [sentence.strip() for sentence in sentences if sentence.strip()]

        # Check if we have enough content
        if len(sentences) < total_items * 0.5:
            log.warning(
                f"[AUDIO_SPLIT] Not enough sentences ({len(sentences)}) for "
                f"{total_items} items. Using single audio."
            )
            return None

        # Distribute sentences across all items
        segments = []
        sentences_per_item = len(sentences) / total_items

        current_segment = []
        target_sentences = sentences_per_item

        for sentence_index, sentence in enumerate(sentences):
            current_segment.append(sentence)

            if len(current_segment) >= target_sentences and len(segments) < total_items - 1:
                segments.append(" ".join(current_segment))
                current_segment = []
                target_sentences = (len(sentences) - sentence_index - 1) / (total_items - len(segments))

        # Add remaining sentences
        if current_segment:
            segments.append(" ".join(current_segment))

        # Validate segments
        segments = [seg for seg in segments if seg and seg.strip() not in ["", ".", ",", "!"]]

        if len(segments) < total_items * 0.5:
            log.warning("[AUDIO_SPLIT] Too many empty segments. Using single audio.")
            return None

        return segments[:total_items]

    # Update your _create_slide_clip method to use the new function
    def _create_slide_clip(self, slide: dict, topic_folder: Path) -> CompositeVideoClip:
        """
        Create a video clip for a single slide.
        Handles progressive bullet reveals including sub-bullets, and slides without bullets.
        """
        try:
            # --- Layout & Padding Definitions ---
            width, height = 1920, 1080
            side_padding = 300
            content_width = width - (2 * side_padding)
            content_width_chars = 70

            # Vertical positions
            title_y = 150
            content_y = 360

            # Check if this slide has bullet timing (progressive reveal)
            has_bullet_timing = slide.get("bullet_audio_segments") is not None
            has_pause = slide.get("has_pause", False)
            bullets = slide.get("bullets", [])

            # Only use progressive reveal if we have both bullet_audio_segments AND actual bullets
            if has_bullet_timing and bullets:
                # Check if any bullets have sub-bullets
                bullets = slide.get("bullets", [])
                has_subbullets = any(
                    isinstance(bullet, dict) and bullet.get("sub_bullets") for bullet in bullets
                )

                if has_subbullets:
                    # Use enhanced sub-bullet function
                    return self._create_progressive_bullet_clip_with_subbullets(
                        slide,
                        topic_folder,
                        width=width,
                        height=height,
                        side_padding=side_padding,
                        content_width=content_width,
                        content_width_chars=content_width_chars,
                        title_y=title_y,
                        content_y=content_y,
                    )
                else:
                    # Use standard progressive bullet function
                    return self._create_progressive_bullet_clip(
                        slide,
                        topic_folder,
                        width=width,
                        height=height,
                        side_padding=side_padding,
                        content_width=content_width,
                        content_width_chars=content_width_chars,
                        title_y=title_y,
                        content_y=content_y,
                    )

            # STANDARD MODE (no progressive reveal) - for slides without bullets
            # Get audio file
            audio_file = topic_folder / "audio" / f"slide_{slide['position']:04d}.wav"
            if not audio_file.exists():
                log.warning(f"[VIDEO_GENERATION] Audio file not found: {audio_file}")
                return None

            audio = AudioFileClip(str(audio_file))
            duration = audio.duration

            # Add pause duration for question slides
            if has_pause:
                pause_duration = slide.get("pause_duration", 3.5)
                total_duration = duration + pause_duration
                log.debug(f"[VIDEO_GENERATION] Question slide with {pause_duration}s pause")
            else:
                total_duration = duration

            image_elements, side_padding, content_width, is_full_image = self._create_image_clips(
                slide,
                topic_folder,
                total_duration,
                width,
                height,
                side_padding,
                content_y,
            )

            # Create background
            background_img_path = self.slides_base_dir / "images" / "bg.png"
            log.debug(f"[VIDEO_GENERATION] Checking background path: {background_img_path}")
            log.debug(f"[VIDEO_GENERATION] Background path exists: {background_img_path.exists()}")
            if not background_img_path.exists():
                background = ColorClip(size=(width, height), color=(245, 245, 247), duration=total_duration)
                elements = [background]
            else:
                background = ImageClip(str(background_img_path)).with_duration(total_duration)
                elements = [background]

            elements.extend(image_elements)

            # Title (with highlights applied as uppercase) - skip for full_image layout
            if not is_full_image:
                title_text = slide["title"]
                highlights = slide.get("highlights", [])
                if highlights:
                    title_text = self._apply_highlights_to_text(title_text, highlights)

                title = (
                    TextClip(
                        text=title_text,
                        font_size=64,
                        color="#FF6262",
                        font=str(self.font_path),
                        stroke_color="#FF6262",
                        stroke_width=1,
                        text_align="center",
                        size=(content_width, 200),
                        method="caption",
                    )
                    .with_duration(total_duration)
                    .with_position(("center", title_y))
                    .with_effects([CrossFadeIn(0.3)])  # Simple fade-in
                )
                elements.append(title)

            # Handle patient explanation slide (no bullets) - skip for full_image layout
            if slide.get("explanation") and not slide.get("bullets") and not is_full_image:
                wrapper = textwrap.TextWrapper(width=content_width_chars)
                wrapped_text = wrapper.fill(text=slide["explanation"])

                explanation = (
                    TextClip(
                        text=wrapped_text,
                        font_size=38,
                        color="#1D1D1F",
                        font="/System/Library/Fonts/HelveticaNeue.ttc",
                        text_align="left",
                        size=(content_width, 600),
                        method="caption",
                    )
                    .with_duration(total_duration)
                    .with_position((side_padding, content_y))
                )
                elements.append(explanation)
            # Handle slides with bullets (but no progressive reveal) - skip for full_image layout
            elif slide.get("bullets") and not is_full_image:
                bullets = slide["bullets"]
                # Handle both string and structured bullets
                if bullets and isinstance(bullets[0], dict):
                    # Structured bullets - format them properly
                    bullet_lines = []
                    for bullet in bullets:
                        if isinstance(bullet, dict):
                            bullet_lines.append(f"• {bullet.get('text', '')}")
                            sub_bullets = bullet.get("sub_bullets", [])
                            for sub in sub_bullets:
                                if isinstance(sub, dict):
                                    bullet_lines.append(f"  - {sub.get('text', '')}")
                                else:
                                    bullet_lines.append(f"  - {sub}")
                        else:
                            bullet_lines.append(f"• {bullet}")
                    bullet_text = "\n\n".join(bullet_lines)
                else:
                    bullet_text = "\n\n".join([f"• {bullet}" for bullet in bullets])

                # Apply highlights
                highlights = slide.get("highlights", [])
                if highlights:
                    bullet_text = self._apply_highlights_to_text(bullet_text, highlights)

                bullets_clip = (
                    TextClip(
                        text=bullet_text,
                        font_size=38,
                        color="#1D1D1F",
                        font=str(self.font_path),
                        method="caption",
                        size=(content_width, 700),
                        horizontal_align="left",
                        vertical_align="top",
                    )
                    .with_duration(total_duration)
                    .with_position((side_padding, content_y))
                )
                elements.append(bullets_clip)

            # Compose all elements
            composite = CompositeVideoClip(elements)

            # Sync audio to this slide
            composite = composite.with_audio(audio)

            log.debug(
                f"[VIDEO_GENERATION] Slide {slide['position']} clip created (duration: {total_duration:.2f}s)"
            )

            return composite

        except Exception as e:
            log.error(f"[VIDEO_GENERATION] Error creating slide clip: {str(e)}", exc_info=True)
            return None
