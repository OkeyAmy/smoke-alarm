#!/usr/bin/env python3
"""Register (or remove) the smoke-alarm PostToolUse hook in each agent's config.

This is what makes smoke-alarm run *internally*: after install, the agent auto-grades
every test file it writes and gets the verdict fed back — no human runs anything.

  register_hooks.py install     merge the hook into present agents (idempotent)
  register_hooks.py uninstall   remove only smoke-alarm's hook entries

Safe by design: it merges into existing config, identifies its own entries by a marker
in the command string, never touches other hooks, and writes a one-time .bak.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HOME = Path.home()
MARKER = "smoke-alarm/hooks/posttooluse.py"
MATCHER = "Write|Edit|MultiEdit"

# (config file, command that runs the hook for that agent). Only applied if present.
TARGETS = [
    (HOME / ".claude" / "settings.json",
     f'python3 "{HOME}/.claude/skills/smoke-alarm/hooks/posttooluse.py"'),
    (HOME / ".codex" / "hooks.json",
     f'python3 "{HOME}/.codex/skills/smoke-alarm/hooks/posttooluse.py"'),
]


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        return {}


def save(path: Path, cfg: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not (path.with_suffix(path.suffix + ".smoke-alarm.bak")).exists():
        (path.with_suffix(path.suffix + ".smoke-alarm.bak")).write_text(
            path.read_text(encoding="utf-8"), encoding="utf-8")
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")


def has_our_hook(cfg: dict) -> bool:
    for group in cfg.get("hooks", {}).get("PostToolUse", []):
        for h in group.get("hooks", []):
            if MARKER in h.get("command", ""):
                return True
    return False


def add_hook(cfg: dict, command: str) -> bool:
    if has_our_hook(cfg):
        return False
    ptu = cfg.setdefault("hooks", {}).setdefault("PostToolUse", [])
    ptu.append({"matcher": MATCHER,
                "hooks": [{"type": "command", "command": command,
                           "statusMessage": "smoke-alarm: grading test oracles"}]})
    return True


def remove_hook(cfg: dict) -> bool:
    ptu = cfg.get("hooks", {}).get("PostToolUse")
    if not ptu:
        return False
    changed = False
    kept = []
    for group in ptu:
        before = len(group.get("hooks", []))
        group["hooks"] = [h for h in group.get("hooks", []) if MARKER not in h.get("command", "")]
        if len(group["hooks"]) != before:
            changed = True
        if group["hooks"]:
            kept.append(group)
    cfg["hooks"]["PostToolUse"] = kept
    return changed


def main(argv: list[str]) -> int:
    action = argv[0] if argv else "install"
    if action not in {"install", "uninstall"}:
        print("usage: register_hooks.py [install|uninstall]", file=sys.stderr)
        return 2

    for path, command in TARGETS:
        if action == "install" and not path.parent.exists():
            continue  # agent not present
        cfg = load(path)
        changed = add_hook(cfg, command) if action == "install" else remove_hook(cfg)
        if changed:
            save(path, cfg)
            print(f"{action}ed hook -> {path}")
        else:
            verb = "already present" if action == "install" else "not present"
            print(f"hook {verb} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
