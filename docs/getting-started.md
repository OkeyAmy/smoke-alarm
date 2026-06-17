# Getting started

Five minutes from clone to a graded test.

## 1. Install

```bash
git clone https://github.com/OkeyAmy/smoke-alarm
cd smoke-alarm
./install.sh
./install.sh doctor
```

`doctor` checks for Python ≥ 3.11 and runs the instrument self-tests. If it is green,
you are ready. Restart your AI tool session so it picks up the new skill.

## 2. See it grade a test

The repo ships labeled fixtures. Grade one:

```bash
python3 skills/smoke-alarm/scripts/grade.py \
  skills/smoke-alarm/tests/fixtures/python/test_examples.py
```

You will see each test function tagged `ALARM` (strong oracle) or `smoke` (weak), with
its taxonomy code (W1–S3). This is **triage** — it sees whether an assertion exists, not
whether it is correct.

## 3. Ask the harder question: where did the expected value come from?

```bash
python3 skills/smoke-alarm/scripts/provenance.py \
  skills/smoke-alarm/tests/fixtures/provenance/test_pricing.py
```

It flags tests whose expected value was copied from the implementation, recorded from
output, taken from an unread snapshot, or compared against another computed value.
These are heuristics for review — not verdicts.

## 4. Prove it dynamically (optional, needs a mutation tool)

```bash
python3 skills/smoke-alarm/scripts/mutate.py path/to/your/source
```

This breaks your code on purpose and reruns the tests. A surviving mutant is a bug your
suite did not notice. Install the tool for your language first — see
[mutation.md](../mutation.md).

## 5. Audit an existing codebase

```bash
python3 skills/smoke-alarm/scripts/audit.py path/to/your/repo --source path/to/src
```

This grades every test, runs provenance, writes `.smoke-alarm/baseline.json`, and
prints a worst-first plan. Fix in batches, then re-run — the baseline ratchets up.

## 6. Gate new tests in CI

Add to CI or a pre-commit hook so new test theater is blocked while your legacy suite
is left alone:

```bash
python3 skills/smoke-alarm/scripts/gate.py --base origin/main
```

It only grades test files that changed, fails on any weak unit, and (if a baseline
exists) fails if overall %strong regressed.

## Using it inside an AI tool

Once installed, the skill auto-triggers whenever the agent writes or edits a test. You
can also invoke it explicitly:

- "write tests for X" → the agent adopts the interrogation loop
- `/smoke-alarm audit` → sweep an existing suite

The agent runs the same instruments above on its own output and fixes anything that
comes back as smoke.
