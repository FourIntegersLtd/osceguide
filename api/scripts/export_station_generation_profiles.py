#!/usr/bin/env python3
"""Export B2C Pydantic Field descriptions into generation profile JSON files.

Run from platform-api: poetry run python scripts/export_station_generation_profiles.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
B2C_API = REPO_ROOT / "backend" / "b2c-api"
OUT_DIR = Path(__file__).resolve().parents[1] / "app" / "features" / "stations" / "generation_profiles" / "_generated"

# Template block id -> B2C model field name when they differ
BLOCK_FIELD_ALIASES: dict[str, str] = {
    "doctor_patient_biodata": "patient_biodata",
}


def _field_hints_from_model(model_cls: type) -> dict[str, str]:
    hints: dict[str, str] = {}
    for name, field in model_cls.model_fields.items():
        desc = field.description
        if isinstance(desc, str) and desc.strip():
            hints[name] = desc.strip()
    return hints


def _merge_hints(*model_classes: type) -> dict[str, str]:
    merged: dict[str, str] = {}
    for model_cls in model_classes:
        merged.update(_field_hints_from_model(model_cls))
    for block_id, field_name in BLOCK_FIELD_ALIASES.items():
        if field_name in merged and block_id not in merged:
            merged[block_id] = merged[field_name]
    return merged


def main() -> None:
    if not B2C_API.is_dir():
        raise SystemExit(f"b2c-api not found at {B2C_API}")
    sys.path.insert(0, str(B2C_API))

    from b2c.casc.models.station.CascStationModel import (  # noqa: PLC0415
        CascDoctorInformationModel,
        CascManagementPlanModel,
        CascPatientInformationModel,
    )
    from b2c.ortho.models.stations.OrthoClinicalStationModel import (  # noqa: PLC0415
        OrthoClinicalStationModel,
    )
    from b2c.ortho.models.stations.OrthoCommunicationStationModel import (  # noqa: PLC0415
        OrthoCommunicationStationModel,
    )
    from b2c.ortho.models.stations.OrthoPortfolioStationModel import (  # noqa: PLC0415
        OrthoPortfolioStationModel,
    )
    from b2c.ortho.models.stations.OrthoPrioritisationStationModel import (  # noqa: PLC0415
        OrthoPrioritisationStationModel,
    )
    from b2c.plab.models.station.PlabStationModel import (  # noqa: PLC0415
        PlabDoctorInformationModel,
        PlabManagementModel,
        PlabPatientInformationModel,
    )
    from b2c.sca.models.stations.StationModel import (  # noqa: PLC0415
        ScaDoctorInformationModel,
        ScaManagementPlanModel,
        ScaPatientInformationModel,
    )

    profiles: list[dict[str, Any]] = [
        {
            "profileKey": "sca.station",
            "label": "SCA consultation station",
            "examCode": "sca",
            "orthoStationType": None,
            "blockHints": _merge_hints(
                ScaPatientInformationModel,
                ScaDoctorInformationModel,
                ScaManagementPlanModel,
            ),
        },
        {
            "profileKey": "plab.station",
            "label": "PLAB 2 station",
            "examCode": "plab",
            "orthoStationType": None,
            "blockHints": _merge_hints(
                PlabPatientInformationModel,
                PlabDoctorInformationModel,
                PlabManagementModel,
            ),
        },
        {
            "profileKey": "casc.station",
            "label": "CASC station",
            "examCode": "casc",
            "orthoStationType": None,
            "blockHints": _merge_hints(
                CascPatientInformationModel,
                CascDoctorInformationModel,
                CascManagementPlanModel,
            ),
        },
        {
            "profileKey": "ortho.clinical",
            "label": "Ortho ST3 clinical",
            "examCode": "ortho",
            "orthoStationType": "clinical",
            "blockHints": _field_hints_from_model(OrthoClinicalStationModel),
        },
        {
            "profileKey": "ortho.communication",
            "label": "Ortho ST3 communication",
            "examCode": "ortho",
            "orthoStationType": "communication",
            "blockHints": _field_hints_from_model(OrthoCommunicationStationModel),
        },
        {
            "profileKey": "ortho.prioritisation",
            "label": "Ortho ST3 prioritisation",
            "examCode": "ortho",
            "orthoStationType": "prioritisation",
            "blockHints": _field_hints_from_model(OrthoPrioritisationStationModel),
        },
        {
            "profileKey": "ortho.portfolio",
            "label": "Ortho ST3 portfolio",
            "examCode": "ortho",
            "orthoStationType": "portfolio",
            "blockHints": _field_hints_from_model(OrthoPortfolioStationModel),
        },
        {
            "profileKey": "custom",
            "label": "Custom (org-defined system prompt)",
            "examCode": None,
            "orthoStationType": None,
            "blockHints": {},
        },
    ]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for profile in profiles:
        key = profile["profileKey"]
        path = OUT_DIR / f"{key.replace('.', '_')}.json"
        path.write_text(json.dumps(profile, indent=2, ensure_ascii=False) + "\n")
        print(f"wrote {path} ({len(profile['blockHints'])} block hints)")

    index = [
        {
            "profileKey": p["profileKey"],
            "label": p["label"],
            "examCode": p.get("examCode"),
            "orthoStationType": p.get("orthoStationType"),
        }
        for p in profiles
    ]
    (OUT_DIR / "index.json").write_text(json.dumps(index, indent=2) + "\n")
    print("done")


if __name__ == "__main__":
    main()
