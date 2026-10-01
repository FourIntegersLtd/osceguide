"""Who may read which block: a block's role decides before its section's audience."""

from app.features.stations.domain_audience import sections_for

# The Ortho prioritisation shape: the examiner's model answer filed inside candidate sections.
PRIORITISATION_SECTIONS = [
    {
        "id": "basic_information",
        "title": "Basic information",
        "audience": "candidate",
        "blocks": [
            {"id": "clinical_scenario", "label": "Scenario", "type": "longText", "role": "candidate_brief"},
            {
                "id": "suggested_order_overview",
                "label": "Suggested order",
                "type": "longText",
                "role": "examiner",
            },
        ],
    },
    {
        "id": "patient_lists",
        "title": "Patient lists",
        "audience": "candidate",
        "blocks": [
            {
                "id": "patient_list_for_candidate",
                "label": "Patients",
                "type": "list",
                "role": "candidate_brief",
            },
            {"id": "examiner_additional_info", "label": "Examiner notes", "type": "list", "role": "examiner"},
        ],
    },
    {
        "id": "patient",
        "title": "Patient",
        "audience": "patient",
        "blocks": [
            {"id": "persona", "label": "Persona", "type": "longText", "role": "persona"},
            {"id": "concerns", "label": "Concerns", "type": "longText", "role": "hidden"},
        ],
    },
]

CONTENT = {
    "clinical_scenario": "You are the registrar on call.",
    "suggested_order_overview": "Open fracture first.",
    "patient_list_for_candidate": ["Bed 1", "Bed 2"],
    "examiner_additional_info": ["Bed 2 is septic."],
    "persona": "A 70-year-old retired teacher.",
    "concerns": "Worried about going home.",
}


def _block_ids(audience: str, *, include_hidden: bool = False) -> dict[str, list[str]]:
    """Each projected section's id mapped to the ids of the blocks it kept."""
    return {
        section.id: [block.id for block in section.blocks]
        for section in sections_for(PRIORITISATION_SECTIONS, CONTENT, audience, include_hidden=include_hidden)
    }


def test_candidate_brief_leaves_out_examiner_blocks_filed_in_candidate_sections() -> None:
    assert _block_ids("candidate") == {
        "basic_information": ["clinical_scenario"],
        "patient_lists": ["patient_list_for_candidate"],
    }


def test_examiner_reads_examiner_blocks_from_any_section() -> None:
    assert _block_ids("examiner") == {
        "basic_information": ["suggested_order_overview"],
        "patient_lists": ["examiner_additional_info"],
    }


def test_patient_actor_gets_hidden_blocks_but_never_examiner_ones() -> None:
    assert _block_ids("patient", include_hidden=True) == {"patient": ["persona", "concerns"]}


def test_hidden_blocks_stay_off_unless_asked_for() -> None:
    assert _block_ids("patient") == {"patient": ["persona"]}


def test_records_blocks_carry_their_template_columns() -> None:
    sections = [
        {
            "id": "ward",
            "title": "Ward",
            "audience": "candidate",
            "blocks": [
                {
                    "id": "patients",
                    "label": "Patients",
                    "type": "records",
                    "role": "candidate_brief",
                    "fields": [{"key": "age", "label": "Age"}, {"key": "summary"}, {"label": "no key"}],
                }
            ],
        }
    ]
    [section] = sections_for(sections, {"patients": [{"age": 70, "summary": "Hip"}]}, "candidate")
    assert section.blocks[0].fields == [
        {"key": "age", "label": "Age"},
        {"key": "summary", "label": "summary"},
    ]


def test_faculty_blocks_reach_the_faculty_audience_and_nobody_else() -> None:
    sections = [
        *PRIORITISATION_SECTIONS,
        {
            "id": "faculty",
            "title": "Faculty",
            "audience": "faculty",
            "blocks": [{"id": "debrief", "label": "Debrief", "type": "list", "role": "faculty"}],
        },
    ]
    content = {**CONTENT, "debrief": ["Ask how the scenario felt."]}

    def reads_debrief(audience: str) -> bool:
        projected = sections_for(sections, content, audience, include_hidden=True)
        return any(block.id == "debrief" for section in projected for block in section.blocks)

    assert reads_debrief("faculty")
    assert not any(reads_debrief(audience) for audience in ("candidate", "patient", "examiner"))


def test_the_engine_layout_carries_table_columns_and_makes_faculty_sections_faculty() -> None:
    """The editor's flat block list has neither; both come from the sections."""
    from app.features.stations.service import _engine_layout

    columns = [{"key": "hr", "label": "HR"}]
    sections = [
        {
            "id": "patient",
            "audience": "patient",
            "blocks": [{"id": "states", "type": "records", "role": "examination", "fields": columns}],
        },
        {
            "id": "faculty",
            "audience": "faculty",
            "blocks": [
                {"id": "debrief", "type": "list"},
                {"id": "answers", "type": "list", "role": "examiner"},
            ],
        },
    ]
    flat = [
        {"id": "states", "role": "examination"},
        {"id": "debrief", "role": "hidden"},
        {"id": "answers", "role": "examiner"},
    ]

    assert _engine_layout(flat, sections) == [
        {"id": "states", "role": "examination", "fields": columns},
        {"id": "debrief", "role": "faculty"},
        {"id": "answers", "role": "examiner"},
    ]
