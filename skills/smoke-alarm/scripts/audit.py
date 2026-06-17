#!/usr/bin/env python3
"""smoke-alarm audit (existing codebases).

Sweeps a repo's tests, combines the static grade (pillar 1) and the provenance scan
(pillar 3), writes a baseline to .smoke-alarm/baseline.json, and prints a ranked plan
of what to fix first. Mutation (pillar 2) is run separately via mutate.py because it
executes code and is slow; this audit links to it but does not invoke it.

The baseline enables the ratchet: gate.py blocks regressions below it.

Usage:
  audit.py <repo-or-tests-dir> [--source <dir> ...] [--json] [--baseline <path>]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grade  # noqa: E402
import provenance  # noqa: E402

DEFAULT_BASELINE = ".smoke-alarm/baseline.json"
SCHEMA_VERSION = 1


@dataclass
class FileAudit:
    path: str
    lang: str
    total: int
    strong: int
    weak_units: list[str]
    provenance_flags: int
    flagged_units: list[str] = field(default_factory=list)

    @property
    def pct_strong(self) -> float:
        return 100.0 * self.strong / self.total if self.total else 0.0

    @property
    def rank_key(self) -> tuple:
        # Worst first: most weak units, then most provenance flags.
        return (-len(self.weak_units), -self.provenance_flags, self.path)


def audit_repo(root: Path, source_args: list[str]) -> list[FileAudit]:
    test_files = [
        p for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix.lower() in grade.EXT_TO_LANG
        and grade.looks_like_test_file(p)
    ] if root.is_dir() else [root]

    audits: list[FileAudit] = []
    for tf in test_files:
        fv = grade.grade_file(tf)
        if fv is None:
            continue
        weak = [u.name for u in fv.units if u.tier == "weak"]
        _, prov_units = provenance.scan_file(tf, source_args)
        flagged = [u.name for u in prov_units if u.flags]
        audits.append(FileAudit(
            path=str(tf), lang=fv.lang, total=fv.total, strong=fv.strong,
            weak_units=weak, provenance_flags=sum(len(u.flags) for u in prov_units),
            flagged_units=flagged,
        ))
    return audits


def build_baseline(audits: list[FileAudit]) -> dict:
    total = sum(a.total for a in audits)
    strong = sum(a.strong for a in audits)
    flags = sum(a.provenance_flags for a in audits)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_units": total,
        "strong_units": strong,
        "pct_strong": round(100.0 * strong / total, 2) if total else 0.0,
        "provenance_flags": flags,
        "files": {
            a.path: {"lang": a.lang, "total": a.total, "strong": a.strong,
                     "pct_strong": round(a.pct_strong, 2),
                     "weak_units": a.weak_units, "provenance_flags": a.provenance_flags}
            for a in audits
        },
    }


def render_plan(audits: list[FileAudit], baseline: dict) -> str:
    lines = [
        f"\n== smoke-alarm audit ==",
        f"{baseline['strong_units']}/{baseline['total_units']} units carry strong "
        f"oracles ({baseline['pct_strong']}%); {baseline['provenance_flags']} "
        f"provenance flags across {len(audits)} test files.\n",
        "Fix worst-first:",
    ]
    worst = [a for a in sorted(audits, key=lambda a: a.rank_key)
             if a.weak_units or a.provenance_flags]
    if not worst:
        lines.append("  nothing weak or flagged — suite looks strong (still prove with mutate.py).")
    for a in worst[:25]:
        bits = []
        if a.weak_units:
            bits.append(f"{len(a.weak_units)} weak")
        if a.provenance_flags:
            bits.append(f"{a.provenance_flags} provenance")
        lines.append(f"  {a.path}  [{a.pct_strong:.0f}% strong]  {', '.join(bits)}")
        for w in a.weak_units[:6]:
            lines.append(f"      weak: {w}")
        for f in a.flagged_units[:6]:
            lines.append(f"      flag: {f}")
    lines.append("\nNext: strengthen the weak oracles, confirm provenance, then prove "
                 "with `mutate.py <source>`. Re-run audit to move the baseline up.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="smoke-alarm audit")
    ap.add_argument("target", help="repo or tests directory to audit")
    ap.add_argument("--source", action="append", default=[],
                    help="implementation source for provenance literal checks")
    ap.add_argument("--baseline", default=None,
                    help=f"where to write the baseline (default {DEFAULT_BASELINE})")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-write", action="store_true", help="do not write baseline.json")
    args = ap.parse_args(argv)

    root = Path(args.target)
    if not root.exists():
        print(f"error: path not found: {root}", file=sys.stderr)
        return 2

    audits = audit_repo(root, args.source)
    baseline = build_baseline(audits)

    if not args.no_write:
        base_root = root if root.is_dir() else root.parent
        out = Path(args.baseline) if args.baseline else base_root / DEFAULT_BASELINE
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
        print(f"baseline written -> {out}")

    if args.json:
        print(json.dumps(baseline, indent=2))
    else:
        print(render_plan(audits, baseline))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
