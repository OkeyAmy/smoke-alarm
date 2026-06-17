# Architecture

smoke-alarm is a **skill** (a personality + procedure an AI agent adopts) backed by a
set of small, single-purpose Python **instruments**. The skill is the product; the
instruments are how the personality checks itself objectively instead of self-judging.

## Why a personality *and* instruments

An agent writes the code and the test from one mental model. If that model is wrong,
both are wrong and the test still passes — the agent "agrees with itself." Research
shows a model judging its own tests is ~50% reliable and self-biased. So:

- The **personality** (`SKILL.md`) makes the agent distrust its own green test and run
  a fixed loop: write → interrogate → check → fix → re-check.
- The **instruments** give deterministic answers the agent cannot rationalize away.

Neither half works alone. Personality without instruments is the 50% trap; instruments
without personality is a linter nobody runs.

## The three pillars

```
1. STATIC      grade.py       Does the test assert anything meaningful?   (triage)
2. DYNAMIC     mutate.py      Does it fail when the code is broken?        (verdict)
3. PROVENANCE  provenance.py  Is the expected value grounded in intent?    (correctness)
```

Static is necessary but not sufficient — no significant correlation between static and
dynamic oracle metrics (TOSEM 10.1145/3715107). Mutation is the dynamic verdict.
Provenance is the only thing that catches a strongly-asserting test that checks the
*wrong* value.

## Instruments

| File | Responsibility | Depends on |
|------|---------------|-----------|
| `scripts/grade.py` | classify each test unit into taxonomy W1–S3 | `patterns/<lang>.toml` |
| `scripts/provenance.py` | flag suspect expected-value sources | `grade` (unit splitting) |
| `scripts/mutate.py` | run + parse mutation tools → survivors, %alarm | the language's mutation tool |
| `scripts/audit.py` | sweep a suite, write baseline, rank a plan | `grade`, `provenance` |
| `scripts/gate.py` | block new weak tests, enforce ratchet | `grade`, `git` |

Each instrument is independently runnable and independently tested. `grade.py` is the
shared core: provenance, audit, and gate all reuse its language detection and unit
splitting, so the four agree on what a "test unit" is.

## Data-driven languages

The per-language knowledge lives in `scripts/patterns/<lang>.toml` — assertion regex
grouped by taxonomy category, plus an optional `unit_guard` (e.g. Rust's `#[test]`).
Adding a language is adding a TOML file and fixtures; no Python changes. See
[adding-a-language.md](adding-a-language.md).

## Known limits (see also the honest audit)

- Unit splitting is line-regex, not AST. It approximates and can mis-slice nested
  functions, table-driven Go subtests, and parametrized pytest. AST is the eventual fix
  for Python and TS.
- The static classifier's real-world precision/recall is unmeasured. The fixtures prove
  patterns fire, not that they generalize.
- Provenance detection is heuristic and flags for review; it never issues a verdict.
- mutate.py parses cargo-mutants and mutmut into structured reports; stryker and
  gremlins currently run and forward exit codes only.
