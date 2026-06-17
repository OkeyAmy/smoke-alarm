# Changelog

All notable changes to smoke-alarm. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); this project is pre-1.0 and the
interfaces may still change.

## [Unreleased]

### Added
- **Auto-grade hook (runs internally)** (`hooks/posttooluse.py` + `hooks/register_hooks.py`):
  a PostToolUse hook the installer merges into `~/.claude/settings.json` and
  `~/.codex/hooks.json`. When the agent writes/edits a test file it is graded
  automatically and the verdict is fed back, so the agent self-corrects without a human
  running anything. Merge is safe (preserves existing config) and idempotent;
  `install.sh uninstall` deregisters it.
- **Pillar 1 — static grade** (`grade.py`): classifies test units into the oracle
  taxonomy W1–S3; data-driven per-language patterns (Rust, Go, TS/JS, Python);
  `--audit`, `--gate`, `--json`. Self-test reproduces all fixture labels (20/20).
- **Pillar 2 — mutation** (`mutate.py`): runs and parses cargo-mutants and mutmut into
  structured survivor lists + a mutation score (%alarm); hardened XML parsing
  (defusedxml when present, DTD/entity guard otherwise). Parser self-test.
- **Pillar 3 — provenance** (`provenance.py`): heuristic scanner flagging
  snapshot-only, self-compare, literal-copied-from-implementation, and
  recorded-from-output oracles. Flags for review, never a verdict. Self-test 5/5.
- **audit.py**: combines grade + provenance, writes `.smoke-alarm/baseline.json`, prints
  a worst-first plan.
- **gate.py**: git-aware new/changed detection, blocks new weak tests, baseline ratchet.
- **install.sh**: idempotent install / doctor / uninstall across Claude, Codex, Cursor,
  and agent skill roots.
- **SKILL.md**: personality-first — a rigorous-engineer/detective discipline with a
  write → interrogate → check → fix loop; scripts as its instruments.
- Docs: getting-started, architecture, adding-a-language, honest audit, contributing.
- CI: self-tests on Python 3.11–3.13.

### Notes
- The κ=0.77 / 86.7% accuracy figure belongs to the *paper's* classifier, not this
  one. This classifier's real-world precision/recall is not yet benchmarked; the static
  grade is triage, and the verdict is mutation + provenance.
