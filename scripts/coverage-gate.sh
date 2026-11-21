#!/usr/bin/env bash
# Coverage contribution gate (ADR-0011 Stage 6, Layer B).
#
# For each `app/*.py` file in the staged diff, runs the suite ONCE and requires
# that file's coverage to be >= 80%, else the commit is blocked. Exits early
# with success when no `app/*.py` file changed (docs/config-only commits).
#
# DB-bound by design: a real per-file coverage number needs the real suite, so
# Postgres must be up (see AGENTS.md "Reproducibility").
set -euo pipefail

FLOOR=80

# Changed `app/*.py` files in the staged diff (added/modified/copied/renamed).
# `-z` keeps paths ver-VVV-batim (no quoting/globbing issues); slurp with NUL.
changed=()
while IFS= read -r -d '' f; do
    case "$f" in
        app/*.py) changed+=("$f") ;;
    esac
done < <(git diff --cached --name-only --diff-filter=ACM -z)

if [ "${#changed[@]}" -eq 0 ]; then
    echo "coverage-gate: no app/*.py changed — skipping."
    exit 0
fi

echo "coverage-gate: ${#changed[@]} app/*.py file(s) changed; running suite once."
FASTAPI_ENV=development uv run coverage run -m pytest tests/ >/dev/null

# Export coverage as JSON once; every file below is read from that one run.
json=$(mktemp)
trap 'rm -f "$json"' EXIT
uv run coverage json -o "$json" >/dev/null

failing=()
for f in "${changed[@]}"; do
    pct=$(
        python3 - "$json" "$f" <<'PY'
import json, sys
data = json.load(open(sys.argv[1]))
path = sys.argv[2]
files = data.get("files", {})
# coverage keys match the cwd-relative path exactly for source=["app"].
entry = files.get(path) or files.get(f"./{path}")
if entry is None:
    sys.exit("missing")
print(entry["summary"]["percent_covered_display"])
PY
    )
    if [ "$pct" = "missing" ]; then
        failing+=("$f (not reported by coverage)")
    elif python3 -c "import sys; sys.exit(0 if float('$pct') < $FLOOR else 1)"; then
        failing+=("$f ($pct% < ${FLOOR}%)")
    fi
done

if [ "${#failing[@]}" -ne 0 ]; then
    echo "coverage-gate FAILED — these changed files are below ${FLOOR}%:"
    for f in "${failing[@]}"; do
        echo "  $f"
    done
    exit 1
fi

echo "coverage-gate: all changed app/*.py files >= ${FLOOR}%."
