Run ruff check on the project at `$ARGUMENTS` (e.g. `/lint foundations/propwatch`).

1. `cd` into `$ARGUMENTS` and run `ruff check .` from there — do not suppress any violations.
2. If no violations, report clean and stop.
3. For each violation:
   - Quote the file, line, and rule code (e.g. `E501`, `F401`).
   - Explain what the rule catches and why this specific instance triggered it.
   - Recommend one of:
     - **Fix**: describe the change needed. Show the diff before applying anything — never auto-fix without displaying what will change first.
     - **Suppress**: if the violation is a false positive or intentional, explain why, then show the exact `# noqa: <code>` comment to add with a justification comment alongside it.
   - Never run `ruff check --fix` or apply any change without first showing the diff and getting confirmation.
