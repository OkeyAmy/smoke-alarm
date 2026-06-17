#!/usr/bin/env bash
# smoke-alarm installer — mirror the skill into each AI coding tool that is present.
#
#   ./install.sh            install (idempotent)
#   ./install.sh doctor     verify the install + dependencies
#   ./install.sh uninstall  remove the skill from every tool dir
#
# It only touches directories named `smoke-alarm` inside known skill roots, so it never
# disturbs your other skills or config.

set -euo pipefail

SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills/smoke-alarm"
SKILL="smoke-alarm"

# Known per-tool skill roots. Missing ones are skipped, not created.
TOOL_ROOTS=(
  "$HOME/.claude/skills"
  "$HOME/.codex/skills"
  "$HOME/.cursor/skills"
  "$HOME/.config/agents/skills"
  "$HOME/.agents/skills"
)

c_red()  { printf '\033[31m%s\033[0m\n' "$*"; }
c_grn()  { printf '\033[32m%s\033[0m\n' "$*"; }
c_dim()  { printf '\033[2m%s\033[0m\n' "$*"; }

check_python() {
  if ! command -v python3 >/dev/null 2>&1; then
    c_red "python3 not found — smoke-alarm's instruments need Python >= 3.11 (tomllib)."
    return 1
  fi
  local v; v="$(python3 -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  local maj min; maj="${v%%.*}"; min="${v##*.}"
  if [ "$maj" -lt 3 ] || { [ "$maj" -eq 3 ] && [ "$min" -lt 11 ]; }; then
    c_red "python3 $v found — need >= 3.11 for tomllib."
    return 1
  fi
  c_grn "python3 $v ok"
}

do_install() {
  [ -d "$SRC" ] || { c_red "source not found: $SRC"; exit 1; }
  check_python || c_red "(installing anyway, but the instruments will not run until Python >= 3.11 is available)"
  local installed=0
  for root in "${TOOL_ROOTS[@]}"; do
    if [ -d "$root" ]; then
      rm -rf "${root:?}/$SKILL"
      cp -r "$SRC" "$root/$SKILL"
      c_grn "installed -> $root/$SKILL"
      installed=$((installed + 1))
    else
      c_dim "skip (not present) -> $root"
    fi
  done
  [ "$installed" -gt 0 ] || { c_red "no known tool skill roots found."; exit 1; }
  echo
  c_dim "registering auto-grade hook (so the agent checks its own tests, no manual run)..."
  python3 "$SRC/hooks/register_hooks.py" install || c_red "hook registration failed (skill still works manually)"
  echo
  c_grn "done. restart your tool session so it reloads the skill + hook."
}

do_uninstall() {
  # deregister the hook first, while the script is still on disk
  if command -v python3 >/dev/null 2>&1 && [ -f "$SRC/hooks/register_hooks.py" ]; then
    python3 "$SRC/hooks/register_hooks.py" uninstall || true
  fi
  local removed=0
  for root in "${TOOL_ROOTS[@]}"; do
    if [ -d "$root/$SKILL" ]; then
      rm -rf "${root:?}/$SKILL"
      c_grn "removed -> $root/$SKILL"
      removed=$((removed + 1))
    fi
  done
  [ "$removed" -gt 0 ] || c_dim "nothing to remove."
}

do_doctor() {
  local ok=0
  check_python || ok=1
  for root in "${TOOL_ROOTS[@]}"; do
    if [ -d "$root" ]; then
      if [ -f "$root/$SKILL/SKILL.md" ]; then
        c_grn "installed: $root/$SKILL"
      else
        c_dim "tool present, skill NOT installed: $root"
      fi
    fi
  done
  echo; c_dim "auto-grade hook status:"
  for cfg in "$HOME/.claude/settings.json" "$HOME/.codex/hooks.json"; do
    if [ -f "$cfg" ] && grep -q "smoke-alarm/hooks/posttooluse.py" "$cfg" 2>/dev/null; then
      c_grn "  hook registered in $cfg"
    elif [ -f "$cfg" ]; then
      c_dim "  hook NOT registered in $cfg (run ./install.sh)"
    fi
  done

  if command -v python3 >/dev/null 2>&1; then
    echo; c_dim "running instrument self-tests..."
    if python3 "$SRC/tests/test_grade.py" >/dev/null 2>&1 \
       && python3 "$SRC/tests/test_provenance.py" >/dev/null 2>&1 \
       && python3 "$SRC/tests/test_mutate.py" >/dev/null 2>&1; then
      c_grn "self-tests pass (grade + provenance + mutate parsers)"
    else
      c_red "self-tests FAILED — run them individually under $SRC/tests/"; ok=1
    fi
  fi
  return $ok
}

case "${1:-install}" in
  install)   do_install ;;
  uninstall) do_uninstall ;;
  doctor)    do_doctor ;;
  *) echo "usage: $0 [install|doctor|uninstall]"; exit 2 ;;
esac
