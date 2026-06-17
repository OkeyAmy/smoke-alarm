# smoke-alarm — Design Spec

**Date:** 2026-06-17
**Status:** Approved (brainstorming → spec)
**Author:** Okey + Claude

---

## 1. Problem

AI coding agents generate test *structure* far more reliably than test *oracles*.
Banik et al., *"All Smoke, No Alarm: Oracle Signals in Agent-Authored Test Code"*
(arXiv:2606.18168, 2026) classified 86,156 agent-authored test patches and found
**80.2% contain weak or no explicit oracle signals** (taxonomy W1–W5), with strong
oracles (S1–S3) on newly-created files ranging only 18%–67% across agents.

A test file existing, and the suite turning green, both *overestimate* verification
strength. Two distinct false positives hide behind a green test:

- **False positive A — checks nothing.** Test executes code, asserts nothing
  meaningful, passes. ("Test theater.")
- **False positive B — checks the wrong thing.** Test asserts what the code
  *currently does* (actual behavior) rather than what it *should do* (expected
  behavior). A bug gets recorded as "expected" and the test guards it forever.
  (Konstantinou et al., arXiv:2410.21136: LLM oracles frequently encode actual,
  not expected, behavior.)

`smoke-alarm` is a portable cross-tool skill that makes coding agents (Claude Code,
OpenAI Codex, Cursor, Copilot, opencode) write tests that actually *alarm* — and
audits/fixes existing tests that only *smoke*.

## 2. Goal & Non-Goals

**Goal:** Whenever any agent writes or edits tests in a codebase, it produces tests
with strong, correctly-grounded oracles; and on demand it audits an existing suite,
reports a truthful baseline, plans fixes, and ratchets quality up without breaking
the build.

**Non-goals:**
- Not a test *runner* or framework — it wraps the codebase's existing runner.
- Not a coverage tool — coverage correlates weakly with fault detection
  (Inozemtseva & Holmes, ICSE 2014).
- Not an LLM-as-judge grader — research shows generate > judge (≈90% vs ≈50%
  valid-assertion rate) and self-judging suffers self-preference bias.

## 3. Why this design (research validation)

| Decision | Evidence |
|---|---|
| Agent **generates** strong oracles (not self-judges) | LLMs produce ≥1 valid assertion in 90%+ of prefixes vs ~50% when classifying; LLM-as-judge has self-preference/position/verbosity bias (arXiv:2506.15227; Adaline; arXiv:2505.16222) |
| Static regex classifier is **triage only**, not the verdict | No significant correlation between static and dynamic oracle metrics (TOSEM 10.1145/3715107) |
| **Mutation** is the dynamic verdict | Mutation score is the principal dynamic test-adequacy metric; coverage is not (ICSE 2014; ISSRE 2023) |
| **Provenance** check for expected values | LLM oracles encode actual not expected behavior (arXiv:2410.21136) — only an implementation-independent source kills false-positive B |
| Regex taxonomy is a *cheap, benchmarked* signal | Paper's own classifier: Cohen κ=0.77, 86.7% agreement with human labels on 384 stratified patches |

## 4. The three pillars

A test is a real **alarm** only if it survives all three checks. Any single failure
marks it **smoke**.

```
1. STATIC     (cheap, instant, every save)
   Regex classify each test unit into the paper taxonomy W1–W5 / S1–S3.
   No assertion / weak-only signal = obvious smoke. Fast pre-filter, NOT the verdict.

2. DYNAMIC    (runs in the real codebase)
   Detect runner (cargo test / go test / pnpm test / pytest), run suite,
   then mutation-test: flip lines in source, rerun. A test still GREEN under a
   mutation = it checks nothing -> kills false-positive A.

3. PROVENANCE (where did the expected value come from?)
   Expected values must trace to intent independent of the implementation:
     OK : docstring / spec / RFC / issue / acceptance criteria / type contract /
          known math or invariant / hand-computed golden value
     BANNED: "run code, copy what it returned" (record-actual, auto-snapshot)
     BANNED: expected literal copied straight from the implementation
   Kills false-positive B.
```

The skill's verdict on "is this test real" = *did it kill the mutant, against an
expected value grounded in intent* — never "does regex see an assert" and never
"is the suite green."

## 5. Two modes

### author mode (auto-trigger when writing/editing tests)
1. **Read first.** Find the repo's existing tests; learn framework, assertion
   style, fixtures, naming. Read the source-under-test and its stated intent
   (docstring/spec/issue) to derive *expected* behavior.
2. **Generate** strong oracle: each test asserts a value / error / type (target
   ≥ S1), covering happy path + boundary + error. Expected values come from intent
   (pillar 3), never from running the code.
3. **Grade** (static) → fix any unit below S1.
4. **Prove** (dynamic) on changed files → mutation must be killed; if a mutant
   survives, the oracle is smoke → rewrite.

### audit mode (`/smoke-alarm audit`, for existing codebases)
1. **Static scan** → fast list of obvious smoke (no/weak assertion), ranked
   new/changed-first (paper: newly-added files carry the strongest signal).
2. **Run suite** → surface broken/red tests.
3. **Mutation run** → per source unit, which mutants survived and which tests
   are therefore smoke.
4. **Provenance scan** → flag oracles whose expected value looks recorded-from-output
   or copied-from-implementation.
5. **Report** real %alarm (mutation-killed + provenance-clean), ranked smoke list,
   write `.smoke-alarm/baseline.json`.
6. **Plan → fix → re-prove**: rewrite weak oracles, re-mutate, confirm they now kill.

## 6. Existing-codebase handling (default case)

- **Gate applies to new/changed test files only** — a legacy suite full of weak
  tests does not fail the build on day one.
- **Baseline + ratchet:** first audit records current %alarm in
  `.smoke-alarm/baseline.json`. The gate blocks *new* smoke (no regression); audit
  chips legacy smoke into alarms over time. Baseline %alarm only moves up.
- No big-bang rewrite, no broken build.

## 7. Components

```
smoke-alarm/                         # github repo root (public, shareable)
  skills/smoke-alarm/
    SKILL.md                         # universal procedure + triggers (name, description)
    references/
      taxonomy.md                    # W1-S3 definitions, paper Table I
      provenance.md                  # expected-value sourcing rules + banned patterns
    scripts/
      grade.py                       # ONE classifier; lang detected by ext
      patterns/{rust,go,ts,python}.toml   # assertion regex per language, data-driven
      mutate.py                      # wraps per-lang mutation runner
    tests/
      fixtures/{rust,go,ts,python}/  # real labeled test files -> classifier self-test
  mutation.md                        # per-lang mutation setup (cargo-mutants/stryker/mutmut/go)
  README.md                          # paper cite, taxonomy, install
  LICENSE
  docs/2026-06-17-smoke-alarm-design.md
```

### grade.py (static classifier — benchmarked core)
```
grade.py <file|dir> [--audit] [--gate] [--json]
 1. detect lang by ext (.rs .go .ts/.tsx .py)
 2. load patterns/<lang>.toml
 3. split file into test units (#[test] / func Test* / it()|test() / def test_)
 4. classify each unit W1..W5 / S1..S3 (highest signal wins)
 5. emit per-test verdict + file summary + %strong
    exit 0 ok | exit 1 when --gate and a new-file unit is weak
```
patterns/<lang>.toml is data-only — adding a language = adding a `.toml`, no code
change. The classifier is self-tested against `tests/fixtures/` with known labels;
reproducing the paper's agreement is the benchmark.

### mutate.py (dynamic verifier)
Detects the runner and the available mutation tool, runs mutation on changed/target
source, maps surviving mutants back to the tests that should have killed them, emits
the real %alarm.

Supported mutation backends (best-effort, degrade gracefully if absent):
- Rust: `cargo-mutants`
- Go: `gremlins` / `go-mutesting`
- TS/JS: `stryker`
- Python: `mutmut` / `cosmic-ray`

## 8. Data flow

```
author:  source+intent ──read──> agent ──generate──> test
              test ──grade.py(static)──> ≥S1? ──no──> rewrite
              test ──mutate.py(dynamic)──> mutant killed? ──no──> rewrite
              expected value ──provenance check──> from intent? ──no──> rewrite

audit:   repo ──grade.py --audit──> smoke list (ranked)
              ──run suite──> red tests
              ──mutate.py──> survived mutants -> smoke tests
              ──provenance scan──> recorded-actual oracles
         ──> baseline.json + plan ──fix──> re-grade + re-mutate ──> prove
```

## 9. Error handling

- **Fail-closed:** if grade/mutation cannot run, the test is treated as *unverified*
  (smoke), never silently passed.
- **Honest limits printed:** static output always states "assertion shape, not
  correctness — run mutation for fault proof."
- **Missing mutation tool:** report it explicitly and fall back to static + provenance;
  never claim a test is a proven alarm without the dynamic check.
- **Confidence reported**, never silent false negatives in the classifier.

## 10. Testing

- `grade.py` self-tested against `tests/fixtures/<lang>/` — real labeled test files,
  not hardcoded-value tests; reproduces the taxonomy classification.
- `mutate.py` tested against a fixture project with one known-good test (kills mutant)
  and one known-smoke test (mutant survives); both verdicts must be correct.
- Provenance scanner tested on fixtures: a spec-grounded oracle (pass) and a
  recorded-from-output oracle (flagged).

## 11. Distribution

```
github.com/okeyamy/smoke-alarm  (public)
  install -> ~/.agents/skills/smoke-alarm (canonical)
          -> register .skill-lock.json (sourceType github)
          -> mirror .claude / .codex / .cursor / .config-agents
          -> /smoke-alarm slash + auto-trigger on test write
```

## 12. Open items (deferred, not blocking v1)

- Mutation runs are slow; v1 mutates changed files only. Whole-repo mutation is a
  later optimization.
- Provenance detection is heuristic (regex + structural); it flags suspicious
  oracles for human/agent review, it does not formally prove provenance.
