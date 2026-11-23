#! /usr/bin/env bash
# One-command exit check: DB up -> full suite + coverage -> pre-commit.
# Mirrors the "done" path in AGENTS.md so a passing check.sh is the done signal.
set -e

docker compose up -d persistence_db
bash scripts/test.sh
uv run pre-commit run --all-files
