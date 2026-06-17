#!/usr/bin/env python3
"""smoke-alarm gate (CI / pre-commit).

Blocks NEW test theater without failing a legacy suite on day one. It grades only the
test files that changed (via git), so existing weak tests are the audit's job, not the
gate's. The paper's own recommendation: flag newly added test files that lack real
assertions.

Two checks:
  1. new/changed test files must have no weak (W1-W5) units
  2. ratchet: overall %strong must not drop below the recorded baseline (if present)

Usage:
  gate.py [--base <ref>] [files...] [--baseline <path>] [--no-ratchet]
  # no files + git repo -> auto-detect changed test files against <base> (default HEAD)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grade  # noqa: E402

DEFAULT_BASELINE = ".smoke-alarm/baseline.json"


def changed_test_files(base: str) -> list[Path]:
    """Test files added or modified vs `base` (staged + unstaged + committed)."""
    cmds = [
        ["git", "diff", "--name-only", "--diff-filter=AM", base],
        ["git", "diff", "--name-only", "--diff-filter=AM", "--cached"],
    ]
    names: set[str] = set()
    for cmd in cmds:
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if out.returncode == 0:
                names.update(line.strip() for line in out.stdout.splitlines() if line.strip())
        except OSError:
            pass
    return [
        Path(n) for n in sorted(names)
        if Path(n).suffix.lower() in grade.EXT_TO_LANG
        and grade.looks_like_test_file(Path(n)) and Path(n).exists()
    ]


def ratchet_ok(baseline_path: Path) -> tuple[bool, str]:
    """Recompute %strong over the files the baseline tracked; fail if it regressed."""
    if not baseline_path.exists():
        return True, "no baseline recorded — ratchet skipped"
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    recorded = data.get("pct_strong", 0.0)
    files = data.get("files", {})
    total = strong = 0
    for path in files:
        p = Path(path)
        if not p.exists():
            continue
        fv = grade.grade_file(p)
        if fv:
            total += fv.total
            strong += fv.strong
    current = round(100.0 * strong / total, 2) if total else 0.0
    if current + 0.001 < recorded:
        return False, f"%strong regressed: baseline {recorded}% -> now {current}%"
    return True, f"%strong held: baseline {recorded}% -> now {current}%"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="smoke-alarm gate")
    ap.add_argument("files", nargs="*", help="explicit test files (default: git-changed)")
    ap.add_argument("--base", default="HEAD", help="git ref to diff against (default HEAD)")
    ap.add_argument("--baseline", default=DEFAULT_BASELINE)
    ap.add_argument("--no-ratchet", action="store_true", help="skip the baseline regression check")
    args = ap.parse_args(argv)

    targets = [Path(f) for f in args.files] if args.files else changed_test_files(args.base)

    failed = False
    if not targets:
        print("smoke-alarm gate: no new/changed test files to check.")
    else:
        print(f"smoke-alarm gate: checking {len(targets)} new/changed test file(s)")
        for t in targets:
            fv = grade.grade_file(t)
            if fv is None:
                continue
            weak = [u for u in fv.units if u.tier == "weak"]
            if weak:
                failed = True
                print(f"  FAIL {t}  ({len(weak)} weak unit(s)):")
                for u in weak:
                    print(f"        [{u.category}] {u.name}")
            else:
                print(f"  ok   {t}  ({fv.strong}/{fv.total} strong)")

    if not args.no_ratchet:
        ok, msg = ratchet_ok(Path(args.baseline))
        print(f"smoke-alarm ratchet: {msg}")
        failed = failed or not ok

    if failed:
        print("\nNew smoke detected. Strengthen the oracles (see /smoke-alarm) before merging.")
        return 1
    print("\nNo new smoke.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
