# Oracle-Signal Taxonomy

From Banik, Chowdhury & Shamim, *"All Smoke, No Alarm: Oracle Signals in
Agent-Authored Test Code"* (arXiv:2606.18168, 2026), Table I.

A **test oracle** is the check that decides whether a test passes or fails. Without
one, a test executes code but never verifies it is correct.

| Code | Tier | Definition | Verdict |
|------|------|------------|---------|
| **W1** | weak | No assertion pattern present | smoke |
| **W2** | weak | Existence / non-null checks only | smoke |
| **W3** | weak | Boolean asserts only (no value compared) | smoke |
| **W4** | weak | Mock / call-verification only | smoke |
| **W5** | weak | Snapshot match only | smoke |
| **S1** | strong | Value equality or comparison | alarm |
| **S2** | strong | Error, containment, or type checks | alarm |
| **S3** | strong | Two or more distinct strong types | alarm |

The *paper's* classifier reached Cohen's κ = 0.77 against two human coders and matched
human labels on **86.7%** of a 384-patch stratified sample. That number describes the
paper's implementation, **not this one**. `grade.py` implements the same taxonomy, but
its accuracy on real-world code has **not been benchmarked** — the current
`tests/fixtures/` only prove the patterns fire on a handful of labeled examples per
language. Measuring precision/recall on a real corpus is tracked in the audit
(`docs/2026-06-17-honest-audit.md`).

## Why weak categories are "smoke"

- **W1** runs code, checks nothing.
- **W2** `x is not None` — the call returned *something*, but nothing about *what*.
- **W3** `assert ok` — a boolean with no value behind it; trivially satisfiable.
- **W4** mock-only — asserts a function was *called*, not that the result was *right*;
  worst case the test mocks the unit under test and passes by construction.
- **W5** snapshot-only — records current output and asserts it does not change; if the
  first recording was wrong, the snapshot guards the bug (see provenance.md).

## Important limit

This taxonomy is **syntactic**. An S1 test (`assertEqual`) confirms an equality check
*exists* — not that it checks the *right* property against the *expected* value. Static
signal is triage. The verdict needs mutation (does it catch a real bug?) and
provenance (is the expected value grounded in intent?).
