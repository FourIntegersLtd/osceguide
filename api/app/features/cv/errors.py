from __future__ import annotations

from app.core.errors import InvalidInput, NotFound


class InvalidCvFile(InvalidInput):
    """A file that is not a readable PDF CV: wrong type, wrong size, no text.

    One code for all of them, with the reason in the message: the client's move
    is identical — tell the person to upload a different file.
    """

    code = "invalid_cv_file"
    default_message = "That file could not be read as a CV"


class CvNotFound(NotFound):
    """No such CV, or one that belongs to somebody else.

    The same answer for both, so an id cannot be probed to learn whose it is.
    """

    code = "cv_not_found"
    default_message = "No such CV"
