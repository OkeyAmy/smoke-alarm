# smoke-alarm — Honest Audit (2026-06-17)

A deep check of what was actually built against (a) the design spec and (b) the bar
set by a proper cross-tool system (oh-my-codex). Written without spin.

## Verdict

About **30% of the design exists**. The part that exists is the *easiest* pillar
(static regex grading), which the design itself calls "triage, not the verdict." The
two pillars that make this tool worth shipping — dynamic mutation mapping and the
provenance scanner — are a launcher shell and a markdown file. There is no installer,
no baseline/ratchet, no new/changed detection, no CI, and no contributor docs. Some
docs claim capabilities that do not exist.

## Overclaims to retract (integrity issues)

1. **"benchmark: κ=0.77 / 86.7% agreement."** That is the *paper's* number for the
   *paper's* classifier. My classifier has 5–6 fixtures per language — that proves the
   patterns fire, not that they generalize. **My tool is not benchmarked.** Saying so
   in README/taxonomy.md was misleading and must be corrected.
2. **mutate.py "maps surviving mutants back to the tests that should have killed
   them, emits the real %alarm."** It does none of that. It shells out to the tool and
   forwards the exit code. The mapping and the %alarm number are vaporware.
3. **SKILL.md tells the agent to run a "provenance scan."** There is no provenance
   scanner. The skill instructs a capability that does not exist.

## Gap analysis vs the design spec

| Spec section | Promised | Built | State |
|---|---|---|---|
| §4 Pillar 1 static | classify W1–S3 | grade.py, 20/20 fixtures | **done** |
| §4 Pillar 2 dynamic | mutate, map mutants→tests, emit %alarm | shell launcher only | **~20%** |
| §4 Pillar 3 provenance | scan oracles for recorded-from-output / copied-from-impl | markdown doc only | **0% (no code)** |
| §5 author mode | read existing tests + source, generate, grade, prove, provenance-check | guidance text in SKILL.md | **guidance only** |
| §5 audit mode | static + run suite + mutation + provenance + baseline.json + ranked plan | static `--audit` only | **~25%** |
| §5 gate mode | gate **new/changed** files only | `--gate` on whatever you pass | **~40% (no git diff)** |
| §6 baseline + ratchet | write baseline.json, block regression, only-goes-up | nothing | **0%** |
| §10 testing | grade + mutate + provenance all tested | only grade tested | **~33%** |
| §11 distribution | installer, .skill-lock.json registration, doctor | manual `cp` loop | **~15%** |

## Gap analysis vs a proper system (oh-my-codex bar)

- **No installer / CLI.** oh-my-codex has `omx setup`/`doctor`/`uninstall` that is
  idempotent and preserves non-managed user config. smoke-alarm has a bash `cp` loop
  that silently overwrites. No verification that the install worked.
- **No CI.** The repo's own self-test and gate do not run on push. A proper system
  runs its own gate on itself (dogfooding).
- **No generated/checked docs.** oh-my-codex generates a catalog and checks it stays in
  sync. smoke-alarm docs drift freely and already contain false claims.
- **No CONTRIBUTING.md, no CHANGELOG.md, no docs/ getting-started.** A newcomer cannot
  add a language or understand the architecture without reading source.
- **No worked examples / no real output in docs.** README shows commands, not results.
- **No requirements stated.** It needs `python3` ≥ 3.11 (tomllib) in every tool
  environment; never documented. No fallback if absent.
- **README missing "what it is NOT", troubleshooting, and an honest accuracy note.**

## Design-level concerns (not just missing code)

1. **Static classifier accuracy is unmeasured and framework-fragile.** Regex per
   framework will miss custom assert helpers and bespoke matchers. Needs (a) a real
   labeled corpus to measure precision/recall, and (b) a documented "unknown → flag,
   never silently pass" policy. Right now an unrecognized assertion silently becomes
   W1 (smoke) — a false positive that will annoy users and erode trust.
2. **Unit splitting is line-regex, not AST.** It will mis-slice nested functions,
   table-driven Go subtests (`t.Run`), parametrized pytest, and `describe` nesting.
   Acceptable for v0 triage but must be labeled as approximate, and AST is the real
   fix for at least Python (`ast`) and TS (ts-morph) eventually.
3. **Provenance detection is genuinely hard.** "Expected value copied from
   implementation" needs cross-file analysis. v1 should ship *heuristics that flag for
   review*, never *auto-verdict*, and say so loudly.
4. **Language choice.** Python scripts ride along fine (no build) but add a python3
   dependency to every tool. oh-my-codex is TS+Rust. Keeping Python is defensible for
   zero-build portability, but it is a real constraint to document, not hide.

## Completion plan (priority order)

**P0 — integrity (do first, cheap):**
1. Retract the false benchmark claim; replace with "patterns validated on fixtures;
   accuracy not yet benchmarked." Fix mutate.py and SKILL.md to not promise the
   unbuilt mapping/provenance.

**P1 — finish the pillars (the actual value):**
2. `provenance.py` — heuristic scanner: flag expected-literal-matches-impl, snapshot-only,
   and record-actual commit patterns. Flags for review, never auto-passes. + tests.
3. `mutate.py` real output parsing for at least cargo-mutants + mutmut: parse survivors,
   map to source locations, emit a real `%alarm`, JSON out. + a fixture project test
   (one killing test, one smoke test).
4. `--audit` writes `.smoke-alarm/baseline.json` and produces a ranked plan; integrate
   provenance + (optional) mutation.

**P2 — make it a system:**
5. Git-aware new/changed detection for gate mode (`--changed` against a base ref);
   ratchet logic (regression check vs baseline).
6. Real installer: `install.sh` (or a small `bin`) that is idempotent, registers in
   `.skill-lock.json`, mirrors tools, and a `doctor` check. `uninstall` too.
7. GitHub Actions CI: run the self-test, run grade.py --gate on the repo's own tests
   (dogfood), check docs.

**P3 — docs for humans:**
8. `docs/getting-started.md`, `docs/adding-a-language.md` (worked example),
   `docs/architecture.md`, `CONTRIBUTING.md`, `CHANGELOG.md`; rewrite README with
   "what it is NOT", requirements, real output, troubleshooting, honest accuracy note.

## What stays

The static classifier core (`grade.py` + pattern TOMLs + fixtures + self-test) is
sound and worth keeping. Everything else is scaffolding around a promise that is not
yet kept.
