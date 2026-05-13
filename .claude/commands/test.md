Run the test suite for the project at `$ARGUMENTS` (e.g. `/test foundations/propwatch`).

1. `cd` into `$ARGUMENTS`, activate its `.venv`, and run `pytest -v` with full output — do not suppress tracebacks or truncate output.
2. If all tests pass, report the count and stop.
3. If any tests fail:
   - Quote the exact error message and traceback for each failure.
   - Explain what the test was asserting and why it failed — diagnose the root cause before suggesting anything.
   - Propose a fix to the production code (or test setup) only after the diagnosis is clear, show the diff, wait for approval before applying.
   - Never delete, skip, or comment out a failing test to make the suite pass.
