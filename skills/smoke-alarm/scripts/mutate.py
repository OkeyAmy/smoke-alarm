#!/usr/bin/env python3
"""smoke-alarm dynamic verifier (pillar 2).

Static grading sees assertion *shape*; only running the tests against deliberately
broken code shows whether they actually *alarm*. This runs the per-language mutation
tool, then parses its result artifact into a structured report: surviving mutants
(tests that should have failed and did not) and the mutation score (%alarm).

Structured parsing is implemented for:
  - cargo-mutants (Rust)  -> mutants.out/outcomes.json
  - mutmut (Python)       -> `mutmut junitxml`
stryker (TS) and gremlins (Go) currently run and forward their exit code; structured
parsing for them is tracked in docs/2026-06-17-honest-audit.md.

If the mutation tool is not installed it says so and exits non-zero (fail-closed)
rather than implying the tests are proven.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:  # prefer the hardened parser when available
    from defusedxml.ElementTree import fromstring as _xml_fromstring
    _XML_HARDENED = True
except ImportError:  # zero-dep fallback: reject DTDs/entities, then use stdlib
    import xml.etree.ElementTree as _ET
    _XML_HARDENED = False

    def _xml_fromstring(text: str):
        lowered = text.lower()
        if "<!doctype" in lowered or "<!entity" in lowered:
            raise ValueError("refusing to parse XML containing a DTD or entity "
                             "declaration (XXE / billion-laughs guard)")
        return _ET.fromstring(text)


@dataclass
class Survivor:
    location: str
    description: str


@dataclass
class MutationReport:
    tool: str
    caught: int = 0
    survived: int = 0
    skipped: int = 0  # unviable / timeout — excluded from the score
    survivors: list[Survivor] = field(default_factory=list)

    @property
    def scored(self) -> int:
        return self.caught + self.survived

    @property
    def pct_alarm(self) -> float:
        return 100.0 * self.caught / self.scored if self.scored else 0.0


# --- parsers (pure functions, unit-tested against real tool output samples) ---

def parse_cargo_mutants(outcomes_json: str) -> MutationReport:
    """Parse cargo-mutants `mutants.out/outcomes.json`."""
    data = json.loads(outcomes_json)
    report = MutationReport(tool="cargo-mutants")
    for outcome in data.get("outcomes", []):
        scenario = outcome.get("scenario")
        if scenario == "Baseline" or not isinstance(scenario, dict):
            continue
        summary = outcome.get("summary", "")
        if summary == "CaughtMutant":
            report.caught += 1
        elif summary == "MissedMutant":
            report.survived += 1
            m = scenario.get("Mutant", {})
            loc = f"{m.get('file', '?')}:{m.get('line', '?')}"
            report.survivors.append(Survivor(loc, m.get("describe", "")))
        else:  # Unviable, Timeout, Failure
            report.skipped += 1
    return report


def parse_mutmut_junitxml(xml_text: str) -> MutationReport:
    """Parse the output of `mutmut junitxml`. A <failure> on a testcase means the
    mutant survived (the suite did not catch it)."""
    report = MutationReport(tool="mutmut")
    root = _xml_fromstring(xml_text)
    for case in root.iter("testcase"):
        failure = case.find("failure")
        error = case.find("error")
        if error is not None:
            report.skipped += 1
        elif failure is not None:
            report.survived += 1
            loc = case.get("name") or case.get("classname") or "?"
            msg = failure.get("message", "survived")
            report.survivors.append(Survivor(loc, msg))
        else:
            report.caught += 1
    return report


# --- backends ---

@dataclass
class Backend:
    lang: str
    tool: str
    check: list[str]
    run: list[str]
    install_hint: str


BACKENDS: dict[str, Backend] = {
    "rust": Backend("rust", "cargo-mutants", ["cargo", "mutants", "--version"],
                    ["cargo", "mutants", "--no-times"], "cargo install cargo-mutants"),
    "python": Backend("python", "mutmut", ["mutmut", "version"],
                      ["mutmut", "run"], "pip install mutmut"),
    "ts": Backend("ts", "stryker", ["npx", "stryker", "--version"],
                  ["npx", "stryker", "run"], "pnpm add -D @stryker-mutator/core"),
    "go": Backend("go", "gremlins", ["gremlins", "--version"],
                  ["gremlins", "unleash", "./..."],
                  "go install github.com/go-gremlins/gremlins/cmd/gremlins@latest"),
}

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


def collect_report(lang: str, workdir: Path) -> MutationReport | None:
    """Locate and parse the tool artifact after a run, where supported."""
    if lang == "rust":
        artifact = workdir / "mutants.out" / "outcomes.json"
        if artifact.exists():
            return parse_cargo_mutants(artifact.read_text(encoding="utf-8"))
    elif lang == "python":
        proc = subprocess.run(["mutmut", "junitxml"], cwd=workdir,
                              capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return parse_mutmut_junitxml(proc.stdout)
    return None


def render_report(report: MutationReport) -> str:
    lines = [f"\nmutation: {report.tool}  {report.pct_alarm:.0f}% alarm "
             f"({report.caught} caught / {report.survived} survived"
             f"{f', {report.skipped} skipped' if report.skipped else ''})"]
    if report.survivors:
        lines.append("  SURVIVING MUTANTS (these tests did not alarm):")
        for s in report.survivors:
            lines.append(f"    - {s.location}  {s.description}")
        lines.append("  Strengthen the oracles covering these lines, then re-run.")
    else:
        lines.append("  no survivors — tests killed every injected bug.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="smoke-alarm dynamic mutation verifier")
    ap.add_argument("target", help="source dir/file under test (used to detect language)")
    ap.add_argument("--lang", choices=sorted(BACKENDS), help="force language")
    ap.add_argument("--json", action="store_true", help="machine-readable report")
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
        return 3

    workdir = target if target.is_dir() else target.parent
    extra = [a for a in args.rest if a != "--"]
    cmd = backend.run + extra
    print(f"smoke-alarm: running {backend.tool}\n  $ {' '.join(cmd)}  (cwd={workdir})\n")
    run_rc = subprocess.run(cmd, cwd=workdir).returncode

    report = collect_report(lang, workdir)
    if report is None:
        print(f"\nsmoke-alarm: ran {backend.tool} (exit={run_rc}) but structured parsing "
              f"is not available for {lang} yet; inspect the tool output above.")
        return run_rc

    if args.json:
        print(json.dumps({
            "tool": report.tool, "pct_alarm": round(report.pct_alarm, 1),
            "caught": report.caught, "survived": report.survived, "skipped": report.skipped,
            "survivors": [{"location": s.location, "description": s.description}
                          for s in report.survivors],
        }, indent=2))
    else:
        print(render_report(report))

    # Non-zero when any mutant survived: those tests are smoke.
    return 1 if report.survived else 0


if __name__ == "__main__":
    raise SystemExit(main())
