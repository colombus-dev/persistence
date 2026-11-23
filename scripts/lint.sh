#!/usr/bin/env bash

set -e
set -x

pyrefly check
pyrefly coverage check
ruff check
ruff format --check
uv run vulture
uv run bandit app
