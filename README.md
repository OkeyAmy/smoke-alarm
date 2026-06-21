# smoke-alarm

> A discipline you give an AI coding agent so it stops trusting its own tests.

`smoke-alarm` is a cross-tool **skill**. When an AI agent (Claude Code, OpenAI Codex,
Cursor, Copilot, opencode) writes a test, the skill makes it *interrogate that test*
before trusting it — and gives it objective instruments to do so, because an agent
judging its own work by feel is only ~50% reliable.

A test that passes is not a test that works. A smoke detector with no battery also
stays silent. This skill is the battery.

---

## The problem

Agents generate test *structure* far more reliably than test *oracles* (the checks
that decide pass/fail). In a study of 86,156 agent-authored test patches, **80.2%
contained weak or no explicit oracle signals** — they run code but never verify it
(Banik, Chowdhury & Shamim, *"All Smoke, No Alarm"*, arXiv:2606.18168, 2026).

Two false positives hide behind a green test:

- **A — checks nothing:** runs the code, asserts nothing meaningful.
- **B — checks the wrong thing:** asserts what the code *currently does*, not what it
  *should do*, so a bug becomes the "expected" value (Konstantinou et al.,
  arXiv:2410.21136).

## The approach: a personality + instruments

The skill gives the agent a character — a rigorous engineer who interrogates each test
like a detective — and the deterministic instruments that character uses, so it never
falls into the self-judging trap:

| Pillar | The question the agent asks itself | Instrument | Catches |
|--------|-----------------------------------|-----------|---------|
| 1. Static | Does it check anything, or just run the code? | `grade.py` | obvious smoke (triage) |
| 2. Dynamic | If the code were wrong, would this test fail? | `mutate.py` | false positive A |
| 3. Provenance | Where did my expected value come from? | `provenance.py` | false positive B |

The loop, every time: **write → interrogate → check with instruments → smoke? fix/plan
→ re-check.** Static is triage, not the verdict — the verdict is mutation + provenance.

## What it is NOT

- **Not a test runner or framework.** It wraps the runner you already use.
- **Not a coverage tool.** Coverage says a line ran, not that the result was checked.
- **Not an LLM-as-judge.** It makes the agent *generate* strong oracles, then verify
  with deterministic instruments — not grade itself by vibes.
- **Not a magic correctness proof.** Provenance flags are heuristics for review;
  passing the instruments raises confidence, it does not guarantee correctness.

## Requirements

- **Python ≥ 3.11** available in each tool's environment (the instruments use
  `tomllib`). The skill's *guidance* works without it; the *instruments* do not.
- For pillar 2 (mutation), the per-language tool — see [mutation.md](mutation.md).
  Optional but strongly recommended; without it the tool refuses to certify a test as
  proven (fail-closed).

## Install

```bash
git clone https://github.com/OkeyAmy/smoke-alarm
cd smoke-alarm
./install.sh            # CLI on PATH + skill files + auto-grade hook
./install.sh doctor     # verify install + run the instrument self-tests
./install.sh uninstall  # remove everything it installed
```

Restart your tool session afterward so it reloads the skill + hook.

Install gives you three ways in, so **any agent** can use it:
1. **`smoke-alarm` command on PATH** — works in any project, any agent: `smoke-alarm grade tests/`.
2. **Skill files** in each AI tool's skills dir, for skill-aware agents.
3. **PostToolUse hook** (Claude Code, Codex) — auto-grades test writes, no human trigger.

### It runs internally — you don't

`install.sh` registers a **PostToolUse hook** in `~/.claude/settings.json` and
`~/.codex/hooks.json` (merged safely — your other settings and hooks are untouched).
The moment the agent writes or edits a test file, the hook auto-grades it and, if it
finds test theater, feeds the verdict straight back to the agent:

```
smoke-alarm: test_user.py has 2 weak oracle(s) — test theater that passes
without verifying behaviour:
  [W4] test_login — mock / call-verification only
  [W1] test_logout — no assertion present
Rewrite each to assert a concrete value, error, or type (>= S1)...
```

The agent then fixes its own test before moving on. No human runs a script. The manual
commands below still exist for audits, CI, and digging in — but the day-to-day path is
automatic. (`/smoke-alarm audit` for an existing suite.)

## Use the instruments directly

With the `smoke-alarm` command on PATH (after install), from inside any project:

```bash
smoke-alarm grade path/to/test_file            # static oracle grade (W1-S3)
smoke-alarm grade --audit path/to/repo         # grade a whole suite
smoke-alarm provenance test_file --source src  # where do expected values come from?
smoke-alarm mutate path/to/source              # mutation: do tests die when code breaks?
smoke-alarm audit path/to/repo --source src    # combined sweep -> baseline + plan
smoke-alarm gate --base origin/main            # CI gate: block NEW weak tests only
```

From a clone without installing, the equivalent is `python3 skills/smoke-alarm/scripts/<name>.py …`.

Example grade output:

```
tests/fixtures/python/test_examples.py  [python]  50% strong (3/6)
    [S1] ALARM  test_value_equality   - value equality or comparison
    [W4] smoke  test_mock_called      - mock / call-verification only
== 3/6 units carry strong oracles (50.0%) ==
NOTE: static = assertion shape, not correctness. Run mutation + provenance before trusting green.
```

## Docs

- [Getting started](docs/getting-started.md) — first run in 5 minutes
- [Architecture](docs/architecture.md) — the three pillars and why
- [Adding a language](docs/adding-a-language.md) — worked example (data-only)
- [Honest audit](docs/2026-06-17-honest-audit.md) — current limitations, no spin
- [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

## Accuracy: read this

The κ=0.77 / 86.7% figure in the paper describes the *paper's* classifier, **not this
one**. `grade.py` implements the same taxonomy but its precision/recall on real code is
**not yet benchmarked** — the fixtures prove the patterns fire, not that they
generalize. The static grade is deliberately *triage*; trust the verdict to mutation +
provenance. Measuring real accuracy is open work (see the honest audit).

## Self-test

```bash
python3 skills/smoke-alarm/tests/test_grade.py        # 20/20 labeled units
python3 skills/smoke-alarm/tests/test_provenance.py   # 5/5 fixtures flagged
python3 skills/smoke-alarm/tests/test_mutate.py       # parsers + XML guard
```

## References

- Banik, Chowdhury & Shamim. *All Smoke, No Alarm.* arXiv:2606.18168 (2026)
- Konstantinou, Degiovanni & Papadakis. arXiv:2410.21136 (2024)
- Inozemtseva & Holmes. *Coverage is not strongly correlated with test suite effectiveness.* ICSE 2014
- Hossain et al. *Measuring and mitigating gaps in structural testing.* ICSE 2023

## License

MIT — see [LICENSE](LICENSE).
