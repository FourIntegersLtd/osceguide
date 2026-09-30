"""Architecture guards.

Each module here states one rule the codebase must obey, scans the source
tree for violations, and proves with a planted violation that the scan is
alive. They run on their own in CI (`make guards`) so a boundary failure is
its own red line. Modelled on `assessment/tests/test_no_consumer_leakage.py`.
"""
