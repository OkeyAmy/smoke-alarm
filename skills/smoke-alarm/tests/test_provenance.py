#!/usr/bin/env python3
"""Self-test for the provenance scanner.

Fixtures under fixtures/provenance/ encode the expected heuristic flag in each test
name: ..._flag_<KIND> means that flag must fire; ..._noflag means none should.

Run:  python3 tests/test_provenance.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "scripts"))

import grade  # noqa: E402
import provenance  # noqa: E402

FLAG_RE = re.compile(r"flag_([A-Z_]+)$")


def expected_flag(name: str) -> str | None:
    if name.endswith("noflag"):
        return ""  # expect no flags
    m = FLAG_RE.search(name)
    return m.group(1) if m else None


def main() -> int:
    fixtures = sorted((ROOT / "fixtures" / "provenance").rglob("*"))
    fixtures = [p for p in fixtures if p.is_file() and p.suffix.lower() in grade.EXT_TO_LANG]
    if not fixtures:
        print("no provenance fixtures found", file=sys.stderr)
        return 2

    total = passed = 0
    failures: list[str] = []
    for fx in fixtures:
        _, units = provenance.scan_file(fx, source_args=[])
        for u in units:
            want = expected_flag(u.name)
            if want is None:
                continue
            total += 1
            got = {f.kind for f in u.flags}
            ok = (want == "" and not got) or (want != "" and want in got)
            if ok:
                passed += 1
            else:
                failures.append(f"{fx.name}::{u.name}  want '{want or 'none'}'  got {sorted(got)}")

    print(f"{passed}/{total} provenance fixtures flagged as expected")
    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("OK — provenance scanner flags every fixture correctly")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
