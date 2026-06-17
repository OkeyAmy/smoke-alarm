#!/usr/bin/env python3
"""smoke-alarm provenance scanner (pillar 3).

The nastiest false positive is a green, strongly-asserting test that checks the
*wrong* value — because the expected value was copied from the implementation or
recorded from a run rather than grounded in intent (Konstantinou et al.,
arXiv:2410.21136).

Static shape (grade.py) and mutation (mutate.py) cannot catch this. This scanner
applies HEURISTICS and FLAGS suspicious oracles for human/spec review. It never
issues a verdict and never certifies a test as correct — absence of a flag is not
proof of good provenance.

Flags:
  SNAPSHOT       snapshot-only assertion; expected value was never human-stated
  SELF_COMPARE   `assert a == b` where both sides are computed, no literal/spec anchor
  LITERAL_IN_IMPL an expected literal also appears verbatim in the implementation
                 source -> the test may just mirror the code
  RECORD_ACTUAL  a comment signals the expected value was recorded from output

Usage:
  provenance.py <test-file> [--source <dir-or-file> ...] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grade  # noqa: E402  (sibling module, reuse lang detection + unit splitting)

# A literal we can compare against the implementation: number, or quoted string.
_NUMBER = r"-?\d+(?:\.\d+)?"
_STRING = r'"[^"\n]*"' + r"|'[^'\n]*'" + r"|`[^`\n]*`"
# When scanning the implementation, numbers must be standalone tokens — otherwise the
# `5` inside an identifier like `expect_W5` would match an expected value of 5.
LITERAL_RE = re.compile(rf"(?<![\w.])(?:{_NUMBER})(?![\w.])|(?:{_STRING})")

# Per-language ways an equality assertion names its expected literal.
EQUALITY_EXPECTED = {
    "python": [
        re.compile(r"assert\s+[^\n=]+==\s*(" + _NUMBER + r"|" + _STRING + r")"),
        re.compile(r"assertEqual\(\s*[^,]+,\s*(" + _NUMBER + r"|" + _STRING + r")"),
    ],
    "ts": [
        re.compile(r"\.toBe\(\s*(" + _NUMBER + r"|" + _STRING + r")\s*\)"),
        re.compile(r"\.toEqual\(\s*(" + _NUMBER + r"|" + _STRING + r")\s*\)"),
    ],
    "go": [
        re.compile(r"assert\.Equal\(\s*t,\s*(" + _NUMBER + r"|" + _STRING + r")"),
        re.compile(r"!=\s*(" + _NUMBER + r"|" + _STRING + r")\s*\{"),
    ],
    "rust": [
        re.compile(r"assert_eq!\(\s*[^,]+,\s*(" + _NUMBER + r"|" + _STRING + r")"),
    ],
}

# `assert a == b` style with two bare identifiers (no literal, no spec anchor).
SELF_COMPARE = {
    "python": re.compile(r"assert\s+([A-Za-z_]\w*)\s*==\s*([A-Za-z_]\w*)\s*$", re.M),
    "ts": re.compile(r"expect\(\s*([A-Za-z_]\w*)\s*\)\.(?:toBe|toEqual)\(\s*([A-Za-z_]\w*)\s*\)"),
    "go": re.compile(r"assert\.Equal\(\s*t,\s*([A-Za-z_]\w*),\s*([A-Za-z_]\w*)\s*\)"),
    "rust": re.compile(r"assert_eq!\(\s*([A-Za-z_]\w*),\s*([A-Za-z_]\w*)\s*\)"),
}

RECORD_ACTUAL_COMMENT = re.compile(
    r"(?:matches?\s+(?:the\s+)?(?:current|existing|actual)\s+(?:output|behaviou?r|value)"
    r"|as\s+returned|whatever\s+it\s+returns?|recorded\s+from|snapshot\s+of\s+current)",
    re.IGNORECASE,
)

SNAPSHOT_HINT = re.compile(
    r"toMatchSnapshot|toMatchInlineSnapshot|assert_snapshot!|assert_debug_snapshot!"
    r"|insta::assert_|cupaloy|MatchSnapshot|goldie\.Assert|==\s*snapshot\b",
)


@dataclass
class Flag:
    kind: str
    detail: str


@dataclass
class UnitProvenance:
    name: str
    flags: list[Flag] = field(default_factory=list)


def implementation_text(test_path: Path, source_args: list[str], ps) -> str:
    """Text to search for copied literals: explicit --source, else the non-test
    portions of the test file itself (impl helpers live there in single-file modules).
    """
    if source_args:
        chunks: list[str] = []
        for s in source_args:
            p = Path(s)
            files = [p] if p.is_file() else [
                f for f in p.rglob("*")
                if f.is_file() and grade.EXT_TO_LANG.get(f.suffix.lower()) == ps.lang
            ]
            for f in files:
                if f.resolve() != test_path.resolve():
                    chunks.append(f.read_text(encoding="utf-8", errors="replace"))
        return "\n".join(chunks)

    full = test_path.read_text(encoding="utf-8", errors="replace")
    # Strip whole units (declaration + body), keeping only non-test code, so test
    # titles and asserted literals never leak into the "implementation" text.
    spans = grade.unit_spans(full, ps)
    kept: list[str] = []
    cursor = 0
    for _name, decl_start, _body_start, end in spans:
        kept.append(full[cursor:decl_start])
        cursor = end
    kept.append(full[cursor:])
    return "".join(kept)


def scan_unit(name: str, body: str, lang: str, impl_text: str) -> UnitProvenance:
    up = UnitProvenance(name=name)

    if SNAPSHOT_HINT.search(body):
        up.flags.append(Flag("SNAPSHOT",
                             "snapshot-only: expected value was never explicitly stated"))

    for m in RECORD_ACTUAL_COMMENT.finditer(body):
        up.flags.append(Flag("RECORD_ACTUAL",
                             f"comment suggests recorded-from-output: '{m.group(0)}'"))

    sc = SELF_COMPARE.get(lang)
    if sc and sc.search(body):
        up.flags.append(Flag("SELF_COMPARE",
                             "compares two computed values with no literal/spec anchor"))

    impl_literals = set(LITERAL_RE.findall(impl_text))
    for pat in EQUALITY_EXPECTED.get(lang, []):
        for m in pat.finditer(body):
            lit = m.group(1)
            if lit in impl_literals and not _is_trivial_literal(lit):
                up.flags.append(Flag("LITERAL_IN_IMPL",
                                     f"expected {lit} also appears in the implementation"))
    return up


def _is_trivial_literal(lit: str) -> bool:
    # 0/1/-1/"" are too common to mean "copied from impl".
    return lit in {"0", "1", "-1", '""', "''", "``"}


def scan_file(test_path: Path, source_args: list[str]) -> tuple[str, list[UnitProvenance]]:
    lang = grade.EXT_TO_LANG.get(test_path.suffix.lower())
    if lang is None:
        return ("", [])
    ps = grade.load_patterns(lang)
    source = test_path.read_text(encoding="utf-8", errors="replace")
    impl_text = implementation_text(test_path, source_args, ps)
    units = [scan_unit(n, b, lang, impl_text) for n, b in grade.split_units(source, ps)]
    return (lang, units)


def render(path: str, lang: str, units: list[UnitProvenance]) -> str:
    flagged = [u for u in units if u.flags]
    lines = [f"\n{path}  [{lang}]  {len(flagged)}/{len(units)} units need provenance review"]
    if not flagged:
        lines.append("    no heuristic flags (NOT a guarantee of good provenance)")
    for u in flagged:
        lines.append(f"    {u.name}")
        for fl in u.flags:
            lines.append(f"      ! {fl.kind}: {fl.detail}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="smoke-alarm provenance scanner (heuristic)")
    ap.add_argument("target", help="test file (or dir) to scan")
    ap.add_argument("--source", action="append", default=[],
                    help="implementation source dir/file to check for copied literals")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.target)
    if not root.exists():
        print(f"error: path not found: {root}", file=sys.stderr)
        return 2

    if root.is_dir():
        targets = [p for p in sorted(root.rglob("*"))
                   if p.is_file() and p.suffix.lower() in grade.EXT_TO_LANG
                   and grade.looks_like_test_file(p)]
    else:
        targets = [root]

    results = []
    any_flag = False
    for t in targets:
        lang, units = scan_file(t, args.source)
        if not lang:
            continue
        results.append((str(t), lang, units))
        any_flag = any_flag or any(u.flags for u in units)

    if args.json:
        payload = [
            {"path": p, "lang": lang,
             "units": [{"name": u.name,
                        "flags": [{"kind": f.kind, "detail": f.detail} for f in u.flags]}
                       for u in units]}
            for p, lang, units in results
        ]
        print(json.dumps(payload, indent=2))
    else:
        for p, lang, units in results:
            print(render(p, lang, units))
        print("\nNOTE: heuristic flags for human/spec review. "
              "No flag is NOT proof of correct provenance. See references/provenance.md.")

    # Exit 1 if anything is flagged, so this can be wired into review gates.
    return 1 if any_flag else 0


if __name__ == "__main__":
    raise SystemExit(main())
