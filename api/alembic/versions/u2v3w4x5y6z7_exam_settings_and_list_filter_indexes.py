"""Per-exam behaviour as data (`exams.settings`), and indexes for new list filters.

`exams.settings` holds what used to be `if exam == "ortho"` branches in the
frontend and the generation prompts: the date label, the debrief modes, the
station subtypes, marking tips, the help dock and the generation prompt keys.
`{}` is a whole exam (every field has a default in `catalog.schemas.
ExamSettings`), so institution exams need no backfill; the four platform
exams are backfilled with what their screens offered before this.

The values are written out here rather than imported, so this revision keeps
meaning what it meant when it ran.

Indexes back the filters added alongside: `specialty=` on media,
`handled=false` on the site inbox, `access_revoked=` on the roster, `status=`
on memberships and `version_ids=` on the station library. The debrief filters
and `sort=published` on media reuse existing indexes.
"""

import json

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "u2v3w4x5y6z7"
down_revision = "t1u2v3w4x5y6"
branch_labels = None
depends_on = None

_SESSION_MODES_BOTH = ["debrief", "practice_as_patient"]

PLATFORM_EXAM_SETTINGS: dict[str, dict[str, object]] = {
    "sca": {
        "date_label": "Exam date",
        "session_modes": _SESSION_MODES_BOTH,
        "station_subtypes": [],
        "show_tips_while_marking": True,
        "help_modes": ["navigate", "knowledge_base"],
        "peer_waiting_email": True,
        "generation": {
            "station_prompt": "sca.station",
            "summary_prompt": "sca.summary",
            "blog_prompt": "sca.blog",
            "default_profile": "sca.station",
        },
    },
    "plab": {
        "date_label": "Exam date",
        "session_modes": _SESSION_MODES_BOTH,
        "station_subtypes": [],
        "show_tips_while_marking": False,
        "help_modes": ["navigate"],
        "peer_waiting_email": False,
        "generation": {
            "station_prompt": "plab.station",
            "summary_prompt": "sca.summary",
            "blog_prompt": "plab.blog",
            "default_profile": "plab.station",
        },
    },
    "casc": {
        "date_label": "Exam date",
        "session_modes": _SESSION_MODES_BOTH,
        "station_subtypes": [],
        "show_tips_while_marking": False,
        "help_modes": ["navigate"],
        "peer_waiting_email": False,
        "generation": {
            "station_prompt": "casc.station",
            "summary_prompt": "casc.summary",
            "blog_prompt": "sca.blog",
            "default_profile": "casc.station",
        },
    },
    "ortho": {
        "date_label": "Interview date",
        "session_modes": ["debrief"],
        "station_subtypes": [
            {"key": subtype, "label": subtype.capitalize(), "generation_profile": f"ortho.{subtype}"}
            for subtype in ("clinical", "communication", "prioritisation", "portfolio")
        ],
        "show_tips_while_marking": False,
        "help_modes": ["navigate"],
        "peer_waiting_email": False,
        "generation": {
            "station_prompt": "ortho.clinical",
            "summary_prompt": "sca.summary",
            "blog_prompt": "sca.blog",
            "default_profile": "ortho.clinical",
        },
    },
}


def upgrade() -> None:
    """Add the settings column, backfill the platform exams, create the filter indexes."""
    op.add_column(
        "exams",
        sa.Column("settings", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    backfill = sa.text(
        "UPDATE exams SET settings = CAST(:settings AS jsonb) WHERE owner_kind = 'platform' AND code = :code"
    )
    for code, settings in PLATFORM_EXAM_SETTINGS.items():
        op.execute(backfill.bindparams(code=code, settings=json.dumps(settings)))

    op.create_index("ix_media_items_kind_specialty", "media_items", ["kind", "specialty"])
    op.create_index(
        "ix_site_messages_unhandled_created",
        "site_messages",
        ["created_at"],
        postgresql_where=sa.text("handled_at IS NULL"),
    )
    op.create_index("ix_trainees_org_access_revoked", "trainees", ["org_id", "access_revoked_at"])
    op.create_index("ix_memberships_org_status", "memberships", ["org_id", "status"])
    op.create_index("ix_stations_current_version_id", "stations", ["current_version_id"])


def downgrade() -> None:
    """Drop the indexes and the settings column."""
    op.drop_index("ix_stations_current_version_id", table_name="stations")
    op.drop_index("ix_memberships_org_status", table_name="memberships")
    op.drop_index("ix_trainees_org_access_revoked", table_name="trainees")
    op.drop_index("ix_site_messages_unhandled_created", table_name="site_messages")
    op.drop_index("ix_media_items_kind_specialty", table_name="media_items")
    op.drop_column("exams", "settings")
