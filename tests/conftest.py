import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402


@pytest.fixture
def seen_dir(tmp_path, monkeypatch):
    """An empty seen_jobs/ directory, so tests never touch the real state."""
    monkeypatch.setattr(config, "SEEN_JOBS_DIR", str(tmp_path))
    import health

    monkeypatch.setattr(health, "HEALTH_FILE", str(tmp_path / "_health.json"))
    return tmp_path
