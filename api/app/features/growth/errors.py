from __future__ import annotations

from app.core.errors import Conflict, Forbidden, InvalidInput, NotFound


class UnknownPartnerError(NotFound):
    code = "unknown_partner"
    default_message = "No such partner"


class ExamNotInPilotError(InvalidInput):
    code = "exam_not_in_pilot"
    default_message = "That exam is not part of the pilot"


class NotAReporter(Forbidden):
    """Reporting access is per partner.

    A reporter for one partner must not be able to read another's numbers, so
    the check is against the partner in the path, not just "is a reporter".
    """

    code = "not_a_partner_reporter"
    default_message = "You do not have reporting access for that partner"


class ReferralCodeTaken(Conflict):
    code = "referral_code_taken"
    default_message = "That referral code is already in use"


class ReferralNotFound(NotFound):
    code = "referral_not_found"
    default_message = "No such referral code"


class ReferralAlreadyRedeemed(Conflict):
    code = "referral_already_redeemed"
    default_message = "That referral code has already been used"


class ReferralNotRedeemed(Conflict):
    """A code nobody has used has no payout to record.

    Paid or unpaid is a fact about a referral that happened; an outstanding
    code is neither.
    """

    code = "referral_not_redeemed"
    default_message = "That referral has not been redeemed, so it has no payout"
