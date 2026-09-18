# Legacy marking snapshots

The committed JSON schemas the two legacy backends asked the marking model to
fill, and the prompts they asked it with, captured from
`b2b-api/tests/fixtures/schemas/` and `b2c-api/b2c/tests/fixtures/schemas/` on
2026-09-17.

They are here because they are the **oracle** for `tests/contract/
test_feedback_model_parity.py`, and because `b2b-api` and `b2c-api` are
scheduled for decommission. Once those repositories are gone, these files are
the only record of what the product marked candidates against, and of the two
places where the two arms had already drifted apart.

Do not edit them. A change in what this platform produces is a change to be
asserted against these, not a reason to update them.
