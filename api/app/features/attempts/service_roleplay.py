"""Read only the actor's script, after the owning learner has finished."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.features.attempts import domain, domain_material, errors
from app.features.attempts.schemas_roleplay import PatientRoleplayRead
from app.features.attempts.service_material import _material_for


async def read_roleplay(
    session: AsyncSession, attempt_id: uuid.UUID, *, requester_id: uuid.UUID
) -> PatientRoleplayRead:
    attempt, material, _ = await _material_for(session, attempt_id, requester_id=requester_id, is_admin=False)
    if not domain.is_reviewable(domain.Status(attempt.status)):
        raise errors.AttemptNotFinished()
    patient = domain_material.block(material.content, domain_material.PATIENT_BLOCKS)
    return PatientRoleplayRead(
        idea=domain_material.lines(patient.get("idea")),
        concerns=domain_material.lines(patient.get("concerns")),
        expectation=domain_material.lines(patient.get("expectation")),
        family_social_history=domain_material.lines(patient.get("family_social_history")),
        past_med_history_allergies=domain_material.lines(patient.get("past_med_history_allergies")),
        questions=domain_material.lines(patient.get("questions")),
        patient_biodata=domain_material.text(patient.get("patient_biodata")),
        gender=domain_material.text(patient.get("gender")),
        opening_sentence=domain_material.text(patient.get("opening_sentence")),
        expanded_history=domain_material.text(patient.get("expanded_history")),
        persona=domain_material.text(patient.get("persona")),
    )
