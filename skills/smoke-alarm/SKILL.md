---
name: smoke-alarm
description: >
  Make agent-written tests actually verify behaviour instead of just executing it.
  Use when writing, editing, generating, or reviewing tests, unit tests, test files,
  assertions, or test coverage in any language (Python, TypeScript/JavaScript, Go,
  Rust). Also use to audit an existing test suite for weak oracles ("test theater"),
  or when the user says "write tests", "add a test", "/smoke-alarm", "audit tests",
  "are these tests real", or asks whether tests actually catch bugs. Auto-triggers
  whenever a test file is being created or modified.
---

# smoke-alarm

Agents generate test *structure* reliably but test *oracles* poorly: ~80% of
agent-authored test patches contain weak or no real assertions (Banik et al. 2026,
arXiv:2606.18168). A test file existing — and the suite turning green — both
overstate how much is actually verified.

A test is a real **alarm** only if it survives three pillars. Any single failure makes
it **smoke**.

```
1. STATIC     does it even assert something meaningful?   -> grade.py   (triage)
2. DYNAMIC    does it fail when the code is broken?        -> mutate.py  (verdict)
3. PROVENANCE is the expected value grounded in intent?    -> human/spec (correctness)
```

Static catches "checks nothing." Mutation catches "checks nothing meaningful even
though it asserts." Provenance catches the nasty one: "checks the *wrong* thing
because the expected value was copied from the implementation."

`SA_DIR` below = this skill's directory.

## Author mode — writing or editing a test (default, auto-trigger)

Do these in order. Do not skip step 1.

1. **Read the codebase first.**
   - Find existing tests; learn the framework, assertion style, fixtures, naming.
     Match them — do not introduce a new style.
   - Read the source under test AND its stated intent (docstring, spec, issue,
     type contract). You need the *expected* behaviour, not the current output.

2. **Write strong oracles.** Each test asserts a concrete value, error, or type
   (target S1 or higher; see `references/taxonomy.md`). Cover happy path, boundaries,
   and error paths. Derive every expected value from intent — never by running the
   code and copying the result (see `references/provenance.md`).

3. **Grade (static triage).**
   ```
   python3 SA_DIR/scripts/grade.py <test-file>
   ```
   Rewrite any unit reported W1–W5 until it is S1 or stronger.

4. **Prove (dynamic).** On the file under test:
   ```
   python3 SA_DIR/scripts/mutate.py <source-dir-or-file>
   ```
   A surviving mutant means a test that should have failed did not — its oracle is
   smoke. Strengthen it and rerun. If the mutation tool is missing, install it
   (`mutation.md`); do not claim the test is proven without it.

5. **Provenance self-check.** For each assertion, state in one sentence: *"this SHOULD
   be X because <source>."* If the only answer is "because that's what the code
   returns," it is smoke — go back to step 1 and find the intended value.

## Audit mode — existing test suite (`/smoke-alarm audit`)

For a codebase that already has tests.

1. **Static scan**, ranked new/changed-first (strongest signal per the paper):
   ```
   python3 SA_DIR/scripts/grade.py --audit <repo-or-tests-dir>
   ```
2. **Run the suite** with the project's own runner; note red/broken tests.
3. **Mutation run** on the source:
   ```
   python3 SA_DIR/scripts/mutate.py <source-dir>
   ```
   Surviving mutants point at the tests that are smoke.
4. **Provenance scan.** Flag oracles whose expected value matches a literal in the
   implementation, snapshot-only tests, and values that look recorded-from-output.
5. **Baseline + plan.** Record current %alarm in `.smoke-alarm/baseline.json`. Group
   the weak tests, note what oracle each needs, and fix in batches — re-grade and
   re-mutate to prove each fix. Do not rewrite the whole suite at once.

## Gate mode — block new test theater (CI / pre-commit)

Apply to **new or changed** test files only, so a legacy suite does not fail day one:
```
python3 SA_DIR/scripts/grade.py --gate <changed-test-files...>
```
Exit non-zero if any unit is weak. The baseline only ratchets up: gate stops new
smoke, audit chips away the legacy.

## Hard rules

- **Fail-closed.** If a check cannot run, the test is *unverified* (smoke), never
  silently passed.
- **Green is not proof.** Never report tests as adequate on a green run alone.
- **Generate, don't self-judge.** Write strong oracles up front; do not rely on
  asking a model to grade its own tests — that is the weakest path (≈50% vs ≈90%).
- **Static is triage, not verdict.** An S1 label is necessary, not sufficient. The
  verdict is mutation + provenance.

## Files

- `scripts/grade.py` — static classifier (taxonomy W1–S3), `--audit`, `--gate`, `--json`
- `scripts/mutate.py` — dynamic mutation wrapper (cargo-mutants / mutmut / stryker / gremlins)
- `scripts/patterns/*.toml` — per-language assertion patterns (data-driven; add a lang = add a file)
- `references/taxonomy.md` — the eight categories and what counts as strong
- `references/provenance.md` — where expected values may and may not come from
- `tests/` — fixtures + self-test proving the classifier reproduces its labels
- `mutation.md` — per-language mutation tool setup
