#!/usr/bin/env python3
"""smoke-alarm dynamic verifier (pillar 2).

Static grading sees assertion *shape*; only running the tests against deliberately
broken code shows whether they actually *alarm*. This wraps the per-language
mutation runner: it flips lines in the source under test, reruns the suite, and
reports surviving mutants — a survivor means some test SHOULD have failed and did
not, so its oracle is smoke.

This is a thin, honest wrapper. If the mutation tool is not installed it says so
and exits non-zero (fail-closed) rather than implying the tests are proven.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Backend:
    lang: str
    tool: str
    check: list[str]      # command proving the tool exists
    run: list[str]        # command running mutation on the target
    install_hint: str


BACKENDS: dict[str, Backend] = {
    "rust": Backend(
        lang="rust",
        tool="cargo-mutants",
        check=["cargo", "mutants", "--version"],
        run=["cargo", "mutants", "--no-times"],
        install_hint="cargo install cargo-mutants",
    ),
    "python": Backend(
        lang="python",
        tool="mutmut",
        check=["mutmut", "version"],
        run=["mutmut", "run"],
        install_hint="pip install mutmut",
    ),
    "ts": Backend(
        lang="ts",
        tool="stryker",
        check=["npx", "stryker", "--version"],
        run=["npx", "stryker", "run"],
        install_hint="pnpm add -D @stryker-mutator/core",
    ),
    "go": Backend(
        lang="go",
        tool="gremlins",
        check=["gremlins", "--version"],
        run=["gremlins", "unleash", "./..."],
        install_hint="go install github.com/go-gremlins/gremlins/cmd/gremlins@latest",
    ),
}

# Reuse the language detection from the static classifier so the two pillars agree.
EXT_TO_LANG = {
    ".py": "python", ".ts": "ts", ".tsx": "ts", ".js": "ts", ".jsx": "ts",
    ".go": "go", ".rs": "rust",
}


def detect_lang(path: Path) -> str | None:
    if path.is_file():
        return EXT_TO_LANG.get(path.suffix.lower())
    counts: dict[str, int] = {}
    for p in path.rglob("*"):
        lang = EXT_TO_LANG.get(p.suffix.lower())
        if lang:
            counts[lang] = counts.get(lang, 0) + 1
    return max(counts, key=counts.get) if counts else None


def tool_available(backend: Backend) -> bool:
    if shutil.which(backend.check[0]) is None:
        return False
    try:
        subprocess.run(backend.check, capture_output=True, check=False, timeout=30)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def run_mutation(backend: Backend, workdir: Path, extra: list[str]) -> int:
    cmd = backend.run + extra
    print(f"smoke-alarm: running mutation with {backend.tool}")
    print(f"  $ {' '.join(cmd)}  (cwd={workdir})\n")
    proc = subprocess.run(cmd, cwd=workdir)
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="smoke-alarm dynamic mutation verifier")
    ap.add_argument("target", help="source dir/file under test (used to detect language)")
    ap.add_argument("--lang", choices=sorted(BACKENDS), help="force language")
    ap.add_argument("rest", nargs=argparse.REMAINDER,
                    help="extra args passed through to the mutation tool")
    args = ap.parse_args(argv)

    target = Path(args.target)
    if not target.exists():
        print(f"error: path not found: {target}", file=sys.stderr)
        return 2

    lang = args.lang or detect_lang(target)
    if lang is None:
        print("error: could not detect language for target", file=sys.stderr)
        return 2

    backend = BACKENDS[lang]
    if not tool_available(backend):
        print(f"smoke-alarm: mutation tool '{backend.tool}' for {lang} is NOT installed.")
        print(f"  install:  {backend.install_hint}")
        print("  Without it, oracle strength CANNOT be proven dynamically (fail-closed).")
        print("  Static grading alone never certifies a test as a real alarm.")
        return 3

    workdir = target if target.is_dir() else target.parent
    extra = [a for a in args.rest if a != "--"]
    rc = run_mutation(backend, workdir, extra)
    if rc == 0:
        print("\nsmoke-alarm: no surviving mutants reported — tests killed the injected bugs.")
    else:
        print(f"\nsmoke-alarm: mutation run exit={rc}. "
              "Surviving mutants = tests that did NOT alarm. Strengthen those oracles.")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
