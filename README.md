# smoke-alarm

A cross-tool AI-agent skill that makes generated tests **actually verify behaviour**
instead of just executing it — and audits existing test suites for "test theater."

Works in Claude Code, OpenAI Codex, Cursor, Copilot, and opencode (any tool that
loads `SKILL.md`-style skills).

## Why

Agents generate test *structure* far more reliably than test *oracles*. In a study of
86,156 agent-authored test patches, **80.2% contained weak or no explicit oracle
signals** — they run code but never check it (Banik, Chowdhury & Shamim, *"All Smoke,
No Alarm: Oracle Signals in Agent-Authored Test Code"*, arXiv:2606.18168, 2026).

A test file existing, and the suite turning green, both *overestimate* verification
strength. Two false positives hide behind green:

- **A — checks nothing:** runs code, asserts nothing meaningful.
- **B — checks the wrong thing:** asserts what the code *currently does*, not what it
  *should do*, so a bug becomes the "expected" value (Konstantinou et al.,
  arXiv:2410.21136).

## How — three pillars

A test is a real **alarm** only if it survives all three. Any failure = **smoke**.

| Pillar | Question | Tool | Catches |
|--------|----------|------|---------|
| 1. Static | Does it assert anything meaningful? | `grade.py` | obvious smoke (triage) |
| 2. Dynamic | Does it fail when the code is broken? | `mutate.py` | false-positive A |
| 3. Provenance | Is the expected value grounded in intent? | spec/docstring/issue | false-positive B |

Static is **triage, not a verdict** — no significant correlation between static and
dynamic oracle metrics (TOSEM 10.1145/3715107). The verdict is mutation + provenance.
The skill makes the agent **generate** strong oracles (≈90% reliable) rather than
**judge** its own tests (≈50%, and biased) (arXiv:2506.15227).

## Layout

```
skills/smoke-alarm/
  SKILL.md                     # the procedure every tool follows + triggers
  scripts/
    grade.py                   # static classifier (taxonomy W1–S3)
    mutate.py                  # dynamic mutation wrapper
    patterns/{rust,go,ts,python}.toml   # per-language assertion patterns (data-driven)
  references/
    taxonomy.md                # the eight oracle-signal categories
    provenance.md              # where expected values may/may not come from
  tests/
    fixtures/{rust,go,ts,python}/   # real labeled test files
    test_grade.py              # self-test: classifier must reproduce the labels
mutation.md                    # per-language mutation tool setup
```

## Usage

```bash
# static grade a test file
python3 skills/smoke-alarm/scripts/grade.py path/to/test_file

# audit a whole suite (ranked new/changed-first)
python3 skills/smoke-alarm/scripts/grade.py --audit path/to/repo

# CI / pre-commit gate on changed test files (exit 1 on weak oracles)
python3 skills/smoke-alarm/scripts/grade.py --gate changed_test_file

# prove oracles dynamically (needs a mutation tool, see mutation.md)
python3 skills/smoke-alarm/scripts/mutate.py path/to/source
```

In an agent, the skill auto-triggers whenever a test file is written or edited; run
`/smoke-alarm audit` for an existing suite.

## Self-test

```bash
python3 skills/smoke-alarm/tests/test_grade.py
# -> 20/20 labeled units classified correctly
```

Adding a language is data-only: drop a `scripts/patterns/<lang>.toml` and labeled
fixtures — no code change.

## References

- Banik, Chowdhury & Shamim. *All Smoke, No Alarm.* arXiv:2606.18168 (2026)
- Konstantinou, Degiovanni & Papadakis. *Do LLMs generate test oracles that capture the
  actual or the expected program behaviour?* arXiv:2410.21136 (2024)
- Inozemtseva & Holmes. *Coverage is not strongly correlated with test suite
  effectiveness.* ICSE 2014
- Hossain et al. *Measuring and mitigating gaps in structural testing.* ICSE 2023

## License

MIT — see [LICENSE](LICENSE).
