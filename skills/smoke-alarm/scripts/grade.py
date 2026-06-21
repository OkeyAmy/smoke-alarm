#!/usr/bin/env python3
"""smoke-alarm static classifier.

Pillar 1 of three (static triage). Classifies each test unit into the oracle-signal
taxonomy of Banik et al. 2026 (arXiv:2606.18168, Table I):

    W1  no assertion present              (weak)
    W2  existence / non-null checks only  (weak)
    W3  boolean asserts only              (weak)
    W4  mock / call-verification only     (weak)
    W5  snapshot match only               (weak)
    S1  value equality or comparison      (strong)
    S2  error, containment, or type check (strong)
    S3  two or more distinct strong types (strong)

This is TRIAGE, not a verdict. A static signal sees assertion *shape*, not
*correctness*: an S1 test can still check the wrong property. Run mutation
(pillar 2) and the provenance check (pillar 3) before trusting any green test.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

PATTERNS_DIR = Path(__file__).resolve().parent / "patterns"

EXT_TO_LANG = {
    ".py": "python",
    ".ts": "ts",
    ".tsx": "ts",
    ".js": "ts",
    ".jsx": "ts",
    ".mjs": "ts",
    ".go": "go",
    ".rs": "rust",
}

STRONG = {"S1", "S2", "S3"}
# Single-label precedence: highest signal wins.
PRECEDENCE = ["S3", "S2", "S1", "W5", "W4", "W3", "W2", "W1"]

# Categories computed by the classifier rather than declared in a pattern table.
COMPUTED_DESCS = {
    "S3": "two or more distinct strong types",
    "W1": "no assertion present",
    "W6": "opaque custom assertion — present but not statically verifiable (confirm with mutation)",
}

# A path/name is treated as a test file only if it looks like one.
TEST_FILE_HINTS = ("test", "spec", "__tests__")


@dataclass
class PatternSet:
    lang: str
    unit_pattern: re.Pattern
    signals: dict[str, list[re.Pattern]]
    descs: dict[str, str]
    unit_guard: re.Pattern | None = None

    # How far back to look for a guard marker (e.g. a Rust #[test] attribute).
    GUARD_LOOKBACK = 160


@dataclass
class UnitVerdict:
    name: str
    category: str
    tier: str
    matched: list[str] = field(default_factory=list)


@dataclass
class FileVerdict:
    path: str
    lang: str
    units: list[UnitVerdict]

    @property
    def strong(self) -> int:
        return sum(1 for u in self.units if u.tier == "strong")

    @property
    def total(self) -> int:
        return len(self.units)

    @property
    def pct_strong(self) -> float:
        return 100.0 * self.strong / self.total if self.total else 0.0


def load_patterns(lang: str) -> PatternSet:
    path = PATTERNS_DIR / f"{lang}.toml"
    if not path.exists():
        raise FileNotFoundError(f"no pattern table for language '{lang}' at {path}")
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    unit_pattern = re.compile(data["unit_pattern"], re.MULTILINE)
    guard_src = data.get("unit_guard")
    unit_guard = re.compile(guard_src) if guard_src else None
    signals: dict[str, list[re.Pattern]] = {}
    descs: dict[str, str] = {}
    for cat, body in data.get("signals", {}).items():
        signals[cat] = [re.compile(p, re.MULTILINE) for p in body.get("patterns", [])]
        descs[cat] = body.get("desc", "")
    return PatternSet(lang=lang, unit_pattern=unit_pattern, signals=signals,
                      descs=descs, unit_guard=unit_guard)


def unit_spans(source: str, ps: PatternSet) -> list[tuple[str, int, int, int]]:
    """Return [(name, decl_start, body_start, end)] for each test unit.

    decl_start..end covers the whole unit (declaration + body); body_start..end is
    the body alone. Spanning to the next unit's declaration, not just the body, lets
    callers strip an entire unit from the source.
    """
    starts = list(ps.unit_pattern.finditer(source))
    spans: list[tuple[str, int, int, int]] = []
    for i, m in enumerate(starts):
        if ps.unit_guard is not None:
            window = source[max(0, m.start() - ps.GUARD_LOOKBACK):m.start()]
            if not ps.unit_guard.search(window):
                continue  # e.g. a Rust fn without a #[test] attribute
        name = m.group(1) if m.groups() else m.group(0).strip()
        end = starts[i + 1].start() if i + 1 < len(starts) else len(source)
        spans.append((name, m.start(), m.end(), end))
    return spans


def split_units(source: str, ps: PatternSet) -> list[tuple[str, str]]:
    """Return [(unit_name, unit_body)] by slicing between unit-start matches."""
    return [(name, source[body_start:end])
            for name, _decl, body_start, end in unit_spans(source, ps)]


def classify_unit(name: str, body: str, ps: PatternSet) -> UnitVerdict:
    matched_cats: list[str] = []
    matched_pats: list[str] = []
    for cat, patterns in ps.signals.items():
        for pat in patterns:
            if pat.search(body):
                matched_cats.append(cat)
                matched_pats.append(f"{cat}:{pat.pattern}")
                break  # one hit per category is enough

    distinct_strong = {c for c in matched_cats if c in STRONG}

    if len(distinct_strong) >= 2:
        category = "S3"
    else:
        category = next((c for c in PRECEDENCE if c in matched_cats), "W1")

    tier = "strong" if category in STRONG else "weak"
    return UnitVerdict(name=name, category=category, tier=tier, matched=matched_pats)


def looks_like_test_file(path: Path) -> bool:
    low = path.as_posix().lower()
    return any(h in low for h in TEST_FILE_HINTS)


def grade_file(path: Path) -> FileVerdict | None:
    lang = EXT_TO_LANG.get(path.suffix.lower())
    if lang is None:
        return None
    if lang == "python":
        # Python gets a real AST grader (precise unit splitting + classification).
        # Other languages use the pattern tables until they get the same treatment.
        from ast_grade import grade_python_file
        return grade_python_file(path)
    ps = load_patterns(lang)
    source = path.read_text(encoding="utf-8", errors="replace")
    units = [classify_unit(n, b, ps) for n, b in split_units(source, ps)]
    return FileVerdict(path=str(path), lang=lang, units=units)


def iter_targets(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    out: list[Path] = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in EXT_TO_LANG and looks_like_test_file(p):
            out.append(p)
    return out


def render_text(verdicts: list[FileVerdict], descs_by_lang: dict[str, dict[str, str]]) -> str:
    lines: list[str] = []
    total_units = total_strong = 0
    for fv in verdicts:
        if not fv.units:
            lines.append(f"  {fv.path}: no test units found")
            continue
        lines.append(f"\n{fv.path}  [{fv.lang}]  {fv.pct_strong:.0f}% strong "
                     f"({fv.strong}/{fv.total})")
        for u in fv.units:
            mark = "ALARM" if u.tier == "strong" else "smoke"
            desc = descs_by_lang.get(fv.lang, {}).get(u.category, "") \
                or COMPUTED_DESCS.get(u.category, "")
            lines.append(f"    [{u.category}] {mark:<5}  {u.name}  - {desc}")
        total_units += fv.total
        total_strong += fv.strong
    pct = 100.0 * total_strong / total_units if total_units else 0.0
    lines.append(f"\n== {total_strong}/{total_units} units carry strong oracles "
                 f"({pct:.1f}%) ==")
    lines.append("NOTE: static = assertion shape, not correctness. "
                 "Run mutation (pillar 2) + provenance (pillar 3) before trusting green.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="smoke-alarm static oracle classifier")
    ap.add_argument("target", help="test file or directory to grade")
    ap.add_argument("--audit", action="store_true",
                    help="recurse a directory and grade every test file")
    ap.add_argument("--gate", action="store_true",
                    help="exit non-zero if any unit is weak (use on new/changed files)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    root = Path(args.target)
    if not root.exists():
        print(f"error: path not found: {root}", file=sys.stderr)
        return 2

    targets = iter_targets(root) if (args.audit or root.is_dir()) else [root]
    verdicts: list[FileVerdict] = []
    descs_by_lang: dict[str, dict[str, str]] = {}
    for t in targets:
        fv = grade_file(t)
        if fv is None:
            continue
        verdicts.append(fv)
        if fv.lang not in descs_by_lang:
            descs_by_lang[fv.lang] = load_patterns(fv.lang).descs

    if args.json:
        payload = [
            {
                "path": fv.path,
                "lang": fv.lang,
                "pct_strong": round(fv.pct_strong, 1),
                "units": [
                    {"name": u.name, "category": u.category, "tier": u.tier}
                    for u in fv.units
                ],
            }
            for fv in verdicts
        ]
        print(json.dumps(payload, indent=2))
    else:
        print(render_text(verdicts, descs_by_lang))

    if args.gate:
        has_weak = any(u.tier == "weak" for fv in verdicts for u in fv.units)
        return 1 if has_weak else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
