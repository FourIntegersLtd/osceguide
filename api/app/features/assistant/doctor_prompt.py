"""Station context for the consulting doctor."""

from typing import Any


def consulting_doctor_instructions(extras: dict[str, Any]) -> str | None:
    station = extras.get("station")
    if not isinstance(station, dict):
        return None

    title = _text(station.get("station_name") or station.get("station_title")) or "this OSCE station"
    exam = _text(station.get("exam_code")) or "OSCE"
    patient_biodata = _text(station.get("station_patient_biodata") or station.get("patient_biodata"))
    patient_name = _text(station.get("station_patient_name") or station.get("patient_name"))
    patient_gender = _text(station.get("station_patient_gender") or station.get("patient_gender"))
    role = _text(station.get("doctor_role") or station.get("doctor_identity"))
    task = _text(station.get("doctor_task") or station.get("task_instructions"))
    scenario = _text(station.get("clinical_scenario") or station.get("background_overview"))
    patient_lines = _lines(station.get("patient_information") or station.get("patient_lines"))
    management_lines = _lines(station.get("management_points") or station.get("management_plan"))
    ice_lines = _lines(station.get("ice"))

    sections = [
        "You are Athena Doctor, a clinician demonstrating an ideal OSCE consultation.",
        (
            "The learner is role-playing the patient. You must speak as the doctor only: "
            "ask questions, explain your thinking naturally, and do not answer for the patient."
        ),
        f"Station: {title}.",
        f"Exam: {exam}.",
    ]
    if patient_name or patient_biodata or patient_gender:
        sections.append(
            "Patient identity: "
            + ", ".join(part for part in (patient_name, patient_biodata, patient_gender) if part)
            + "."
        )
    if role:
        sections.append(f"Your role: {role}.")
    if task:
        sections.append(f"Your task: {task}.")
    if scenario:
        sections.append(f"Scenario: {scenario}.")
    if patient_lines:
        sections.append("Patient-facing information to elicit:\n" + _bullets(patient_lines))
    if ice_lines:
        sections.append("Ideas, concerns and expectations to explore:\n" + _bullets(ice_lines))
    if management_lines:
        sections.append("Good consultation should cover:\n" + _bullets(management_lines))
    sections.append(
        "Run the consultation in a realistic OSCE style. Start with identity/consent, "
        "explore the presenting problem, ICE, red flags and relevant background, then "
        "summarise and explain the plan. Keep questions concise and wait for the learner's "
        "patient answers."
    )
    return "\n\n".join(sections)


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _lines(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [line.strip(" -•\t") for line in value.splitlines() if line.strip(" -•\t")]
    if isinstance(value, dict):
        out: list[str] = []
        for key, item in value.items():
            if isinstance(item, list):
                out.extend(f"{key}: {line}" for line in _lines(item))
            elif _text(item):
                out.append(f"{key}: {_text(item)}")
        return out
    return []


def _bullets(lines: list[str]) -> str:
    return "\n".join(f"- {line}" for line in lines)
