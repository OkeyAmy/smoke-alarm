#!/usr/bin/env python3
"""smoke-alarm PostToolUse hook.

Registered on Write/Edit so that the moment an agent writes or edits a test file, its
oracles are graded automatically and the verdict is fed back to the agent — no human
runs anything. This is what makes the discipline internal instead of a script someone
has to remember to run.

Contract (Claude Code / Codex PostToolUse):
  - stdin: JSON with tool_name and tool_input.file_path
  - exit 0: silent, nothing to say
  - exit 2: stderr is surfaced to the agent as feedback (used to report smoke)

Fail behaviour: if the event isn't a gradeable test-file write, exit 0 quietly (do not
nag). If grading a real test file errors, exit 2 so the agent knows it could not be
verified (fail-closed) rather than assuming it's fine.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))


def _read_event() -> dict:
    try:
        return json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return {}


def _file_path(event: dict) -> str | None:
    ti = event.get("tool_input") or {}
    return ti.get("file_path") or ti.get("path") or ti.get("filePath")


def main() -> int:
    event = _read_event()
    fp = _file_path(event)
    if not fp:
        return 0  # not a file-writing tool event

    path = Path(fp)
    try:
        import grade
    except Exception:  # skill not fully installed; don't break the agent
        return 0

    if path.suffix.lower() not in grade.EXT_TO_LANG or not grade.looks_like_test_file(path):
        return 0  # not a test file — nothing to grade
    if not path.exists():
        return 0

    # Skip intentional sample/data files — they are deliberately weak by design.
    posix = path.as_posix().lower()
    if any(part in posix for part in ("/fixtures/", "/testdata/", "/__fixtures__/")):
        return 0
    try:
        if "smoke-alarm: ignore" in path.read_text(encoding="utf-8", errors="replace"):
            return 0  # explicit opt-out marker in the file
    except OSError:
        return 0

    try:
        fv = grade.grade_file(path)
    except Exception as exc:  # a real test file we could not grade -> fail closed
        print(f"smoke-alarm: could not grade {path.name} ({exc}); "
              f"verify its oracles manually before trusting it.", file=sys.stderr)
        return 2

    if fv is None or not fv.units:
        return 0

    weak = [u for u in fv.units if u.tier == "weak"]
    if not weak:
        return 0  # all units carry strong oracles at the static level

    descs = grade.load_patterns(fv.lang).descs
    lines = [f"smoke-alarm: {path.name} has {len(weak)} weak oracle(s) — test theater "
             f"that passes without verifying behaviour:"]
    for u in weak:
        desc = descs.get(u.category, "") or grade.COMPUTED_DESCS.get(u.category, "")
        lines.append(f"  [{u.category}] {u.name} — {desc}")
    lines.append("Rewrite each to assert a concrete value, error, or type (>= S1). Then "
                 "prove it with mutate.py and check provenance.py. Static grade is triage, "
                 "not the verdict — see the smoke-alarm skill.")
    print("\n".join(lines), file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
