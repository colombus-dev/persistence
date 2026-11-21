"""Tests for app settings (config layer, C3).

Confirms the settings read from a repo-root ``.env`` via a relative path that
is portable across clones and CI (no hard-coded developer path).
"""

from pathlib import Path

from app.core.config import Settings


def test_env_file_is_relative_dotenv() -> None:
    """The dotenv path is a portable relative ``.env`` at the repo root, not a
    machine-specific absolute path."""
    env_file = Settings.model_config["env_file"]
    assert env_file == ".env"
    # The working directory the app runs from holds that .env.
    assert (Path.cwd() / env_file).is_file()
