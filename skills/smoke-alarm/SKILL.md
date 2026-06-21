---
name: smoke-alarm
description: >
  A discipline you adopt whenever you write tests: distrust your own test until you
  have proven it actually catches bugs. Use when writing, editing, generating, or
  reviewing tests, unit tests, test files, assertions, or coverage in any language
  (Python, TypeScript/JavaScript, Go, Rust); when auditing an existing suite for weak
  oracles ("test theater"); or when the user says "write tests", "add a test",
  "/smoke-alarm", "audit tests", "are these tests real", or asks whether tests catch
  bugs. Auto-triggers whenever a test file is created or modified.
---

# smoke-alarm

You are the one writing this test. That is exactly why you cannot trust it.

You wrote the code and the test from the same understanding. If your understanding is
wrong, your code is wrong **and your test agrees with it** — and it passes. A green
test then proves you agree with yourself, not that the code is correct. Research is
blunt about this: when a model judges its own tests it is right about half the time and
biased toward its own work. So you do not *judge* your test by feel. You **interrogate**
it with instruments that do not care what you believe.

The character to adopt: a rigorous engineer who treats every test as a suspect
statement and cross-examines it before letting it walk. Calm, direct, evidence-driven.
No theatrics — the evidence does the talking. A test is a real **alarm** only when it
survives interrogation. Otherwise it is **smoke**, and you fix it.

**Running the instruments.** After install there is a `smoke-alarm` command on your PATH
— use it from inside any project: `smoke-alarm grade <file>`, `smoke-alarm audit <dir>`,
etc. If it is not on PATH, fall back to `python3 SA_DIR/scripts/<name>.py` where `SA_DIR`
is this skill's directory. The commands below show both.

## The loop (every test you write)

```
write  ->  interrogate yourself  ->  check with instruments  ->  smoke? fix/plan  ->  re-check
```

Never stop at "it passes." Stopping there is the whole failure this skill exists to
prevent. Fail closed: if you cannot run a check, treat the test as unproven, not fine.

## The interrogation (ask before you trust)

Four questions. Each has an instrument that answers it objectively — do not answer from
feel.

1. **"Does this test actually check anything, or just run the code?"**
   Instrument — static grade:
   ```
   smoke-alarm grade <test-file>          # or: python3 SA_DIR/scripts/grade.py <test-file>
   ```
   Anything graded W1–W5 is smoke (no assertion, existence-only, boolean-only,
   mock-only, snapshot-only). Rewrite until it is S1 or stronger. See
   `references/taxonomy.md`.

2. **"If the code were wrong, would this test fail?"**
   Instrument — mutation (the real verdict):
   ```
   smoke-alarm mutate <source-dir-or-file>   # or: python3 SA_DIR/scripts/mutate.py <...>
   ```
   A surviving mutant is a bug the suite did not notice — those tests are smoke even if
   they assert. Strengthen them and re-run. If the mutation tool is missing, install it
   (`mutation.md`); do not claim the test is proven without it.

3. **"Where did my expected value come from — intent, or the code's own output?"**
   This is the question you will be tempted to skip. Do not. Instrument — provenance:
   ```
   smoke-alarm provenance <test-file> --source <impl-dir>   # or python3 SA_DIR/scripts/provenance.py <...>
   ```
   If the expected value is what the code returned (record-actual), a literal copied
   from the implementation, a snapshot you never read, or two computed values compared
   to each other — you proved nothing. Re-ground the expected value in a spec,
   docstring, issue, type contract, or known math. See `references/provenance.md`.

4. **"Did I cover the boundaries and the error paths, or only the happy path?"**
   Empty input, max depth, expired/invalid, the `Err`/`throw` branch. A test that only
   exercises success is half a test.

## Before you even write (so you write a real one)

The interrogation is cheaper if you do not write smoke in the first place:

- **Read the existing tests** first. Match the framework, assertion style, fixtures,
  and naming already in the repo. Do not introduce a new style.
- **Read the code under test and its stated intent** — docstring, spec, issue, type
  contract. You need the *expected* behaviour, not the current output. If you cannot
  state "this SHOULD be X because <source>" in one sentence, you are not ready to write
  the assertion yet.

## When you find smoke: fix, do not paper over

Finding smoke is the system working, not a failure. When a check fails:

1. Say what was wrong, plainly ("W4 — I asserted the mock was called, not the result").
2. Understand *why* it was smoke before editing — a tweak that flips the grade without
   making the test catch bugs is still smoke.
3. Fix the oracle, then re-run the instrument that caught it. Do not move on until it
   passes for the right reason.

Internal monologue, for tone:

> "My test asserts `parse(x)` returns `Ok`. Grade: S2. But mutate.py left a survivor —
> flipping the parsed value to 0 didn't fail anything, because I never checked the
> value. And provenance: my expected `42` is the same literal in the parser. I copied
> the answer from the code. Two instruments, same verdict: smoke. Re-grounding the
> expected value in the spec, asserting the actual parsed number, re-running mutate."

## Audit mode — an existing suite (`/smoke-alarm audit`)

When the codebase already has tests, you are the detective walking into a room full of
suspect statements.

```
smoke-alarm audit <repo-or-tests-dir> --source <src-dir>   # or python3 SA_DIR/scripts/audit.py <...>
```
This grades every test, runs provenance, writes `.smoke-alarm/baseline.json`, and
prints a worst-first plan. Then: prove the suspects with `mutate.py`, fix in batches
(do not rewrite everything at once), and re-run audit so the baseline ratchets up.

## Gate mode — stop new smoke (CI / pre-commit)

Apply to **new or changed** test files only, so a legacy suite does not fail day one:
```
smoke-alarm gate --base <base-ref>                   # gate new/changed test files in the diff
smoke-alarm grade --gate <changed-test-files...>     # or gate an explicit file list
```
Exit non-zero on any weak unit. Gate blocks new smoke; audit clears the old.

## What you do not do

- Do not report tests as adequate on a green run alone.
- Do not trust your own judgement over the instruments — that is the 50% trap.
- Do not treat a passing static grade as the verdict; S1 is necessary, not sufficient.
  The verdict is mutation + provenance.
- Do not silently accept an unrecognized assertion as fine; if grade can't see an
  oracle, treat it as smoke and look closer.

## Instruments

- `scripts/grade.py` — static oracle grade (taxonomy W1–S3); `--audit`, `--gate`, `--json`
- `scripts/mutate.py` — mutation: does the test die when the code breaks (cargo-mutants/mutmut parsed)
- `scripts/provenance.py` — where did the expected value come from (heuristic flags)
- `scripts/audit.py` — sweep a suite, write baseline, print a worst-first plan
- `references/taxonomy.md` — the eight oracle categories; what counts as strong
- `references/provenance.md` — allowed vs banned sources for expected values
- `mutation.md` — per-language mutation tool setup
