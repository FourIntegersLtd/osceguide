from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Literal, Union


class BulletAudioSegment(BaseModel):
    """Audio timing information for a single bullet point"""

    bullet_index: int = Field(..., description="Index of the bullet (0-based)")
    audio_path: str = Field(..., description="Path to the audio file for this bullet")
    duration: float = Field(
        ..., description="Duration of this audio segment in seconds"
    )
    start_time: float = Field(..., description="Start time of this bullet in the slide")
    text: Optional[str] = Field(
        default=None, description="Text content of this audio segment"
    )


class SubBullet(BaseModel):
    """Represents a sub-bullet point under a main bullet"""

    text: str = Field(..., description="Text content of the sub-bullet")
    highlights: List[str] = Field(
        default=[], description="Optional highlights for this sub-bullet"
    )


class Bullet(BaseModel):
    """Represents a bullet point, optionally with sub-bullets"""

    text: str = Field(..., description="Text content of the main bullet")
    highlights: List[str] = Field(
        default=[], description="Optional highlights for this bullet"
    )
    sub_bullets: List[SubBullet] = Field(
        default=[], description="Optional sub-bullets under this bullet"
    )


class IndividualSlide(BaseModel):
    """Represents a single slide in the teaching video"""

    # AI-generated content
    title: str = Field(
        ..., description="Title of the slide - should be clear and conversational"
    )
    layout: Literal[
        "text_only",
        "text_image_right",
        "text_image_left",
        "full_image",
        "split_screen",
        "triple_image",
    ] = Field(default="text_image_right", description="Layout template for the slide")
    bullets: Optional[Union[List[str], List[Bullet]]] = Field(
        default=None,
        description="1-8 bullet points. Can be simple strings OR structured objects with 'text', 'highlights', and 'sub_bullets' fields. Use structured format with sub_bullets for complex slides (e.g., management strategies, investigations, scoring systems). For simple string bullets, use 2-8 items. For structured bullets with sub_bullets, 1-8 main bullets are allowed (as long as they have sub_bullets). For differentials: 'Condition (1-2 short questions)'. For history/ICE slides: each bullet is ONE direct question e.g., 'Is this based on personal conviction or external pressure?', 'Ideas: What do you think this involves?'. Set to null for question slides and patient explanation slides.",
    )
    highlights: List[str] = Field(
        default=[],
        description="Maximum 1-2 most critical terms/values only - highly selective",
    )
    speaker_notes: str = Field(
        ...,
        min_length=50,
        max_length=800,
        description="Narration script - technical colleague-to-colleague tone suitable for TTS",
    )
    explanation: Optional[str] = Field(
        default=None,
        min_length=100,
        max_length=500,
        description="ONLY for patient explanation slides. Direct quote using MUACW TRAIN principles (empathy, analogies, avoid jargon). Leave null for all other slides.",
    )

    # System-generated metadata (populated by service layer after AI generation)
    position: Optional[int] = Field(
        default=None, description="Position of the slide in the sequence (1-indexed)"
    )
    id: Optional[str] = Field(
        default=None,
        description="Unique identifier for this slide (e.g., 'slide_0001')",
    )
    audio_url: Optional[str] = Field(
        default=None, description="URL to the generated audio file for this slide"
    )
    audio_duration: Optional[float] = Field(
        default=None, description="Duration of the audio in seconds"
    )
    bullet_audio_segments: Optional[List[BulletAudioSegment]] = Field(
        default=None,
        description="Audio timing for each bullet with progressive reveal information",
    )
    has_pause: Optional[bool] = Field(
        default=None,
        description="Whether this slide has a pause (e.g., question slides)",
    )
    pause_duration: Optional[float] = Field(
        default=None,
        description="Duration of the pause in seconds (typically 3-4s for question slides)",
    )
    image_urls: Optional[List[str]] = Field(
        default=None,
        description="URL to an image for this slide. When set, bullets and explanation must be null.",
    )
    video_segment_url: Optional[str] = Field(
        default=None, description="URL to the video segment for this slide"
    )
    slide_duration: Optional[float] = Field(
        default=None, description="Total duration of this slide in seconds"
    )
    start_time: Optional[float] = Field(
        default=None, description="Start time of this slide in the final video"
    )
    end_time: Optional[float] = Field(
        default=None, description="End time of this slide in the final video"
    )

    @model_validator(mode="after")
    def validate_image_slide_requirements(self):
        """Validate that slides with images don't have explanations"""
        if self.image_urls:
            if self.explanation is not None:
                raise ValueError(
                    "Slides with images cannot have explanations. Set explanation to None when image_url is provided."
                )
            if self.layout not in [
                "full_image",
                "text_image_right",
                "text_image_left",
                "split_screen",
                "triple_image",
            ]:
                raise ValueError(
                    f"Slides with images must use a compatible layout. Current layout '{self.layout}' is not compatible with images."
                )
        return self


class SlideGenerationResponse(BaseModel):
    """Complete response for slide generation"""

    topic: str = Field(..., description="Topic of the slides - brief clinical summary")
    about: str = Field(
        ...,
        min_length=50,
        max_length=300,
        description="Brief description of what this teaching video covers. Format: 'In this video, you will learn...' or 'In this course, we discuss...' Examples: 'In this course, we discuss managing an unplanned pregnancy in a woman with epilepsy, covering assessment strategies, medication safety considerations, and multidisciplinary care coordination throughout pregnancy.'",
    )

    # AI-generated content (required)
    slides: List[IndividualSlide] = Field(
        ...,
        min_length=18,
        max_length=24,
        description="List of all slides in the presentation (18-24 slides for interactive format - MUST include conclusion slide)",
    )

    # System-generated metadata (populated by service layer after AI generation)
    slide_id: Optional[str] = Field(
        default=None, description="Unique identifier for this slide job"
    )
    slides_count: Optional[int] = Field(
        default=None, description="Total number of slides"
    )
    total_duration: Optional[float] = Field(
        default=None, description="Total duration of the final video in seconds"
    )
    final_video_url: Optional[str] = Field(
        default=None, description="URL to the final combined video"
    )
    status: Optional[
        Literal["draft", "generating_audio", "generating_video", "completed", "failed"]
    ] = Field(
        default=None, description="Current status of the slide generation process"
    )
    created_by: Optional[str] = Field(
        default=None, description="User ID of the creator"
    )
    created_at: Optional[str] = Field(
        default=None, description="ISO timestamp of creation"
    )
    updated_at: Optional[str] = Field(
        default=None, description="ISO timestamp of last update"
    )
    specialty: Optional[str] = Field(
        default=None, description="Medical specialty associated with this slide set"
    )
