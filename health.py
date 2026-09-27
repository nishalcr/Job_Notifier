"""Per-company scraper health tracking.

A company is marked broken after FAILURE_THRESHOLD consecutive failed runs and
healthy again on its next successful run. Callers alert only on those
transitions, so a site that stays broken does not spam Telegram every run.

Healthy entries never change between runs, so the committed health file only
produces a diff when something actually fails.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

import config

FAILURE_THRESHOLD = int(os.getenv("HEALTH_FAILURE_THRESHOLD", "3"))
HEALTH_FILE = os.path.join(config.SEEN_JOBS_DIR, "_health.json")

BROKEN = "broken"
RECOVERED = "recovered"


def load_health() -> dict[str, Any]:
    if not os.path.exists(HEALTH_FILE):
        return {}
    try:
        with open(HEALTH_FILE, "r") as handle:
            data = json.load(handle)
    except (json.JSONDecodeError, IOError):
        return {}
    return data if isinstance(data, dict) else {}


def save_health(health: dict[str, Any]) -> None:
    os.makedirs(config.SEEN_JOBS_DIR, exist_ok=True)
    with open(HEALTH_FILE, "w") as handle:
        json.dump(health, handle, indent=2, sort_keys=True)
        handle.write("\n")


def record_result(health: dict[str, Any], slug: str, ok: bool, error: str = "") -> str | None:
    """Update a company's health entry. Returns BROKEN, RECOVERED, or None."""
    entry = health.get(slug) or {}
    was_broken = entry.get("status") == BROKEN

    if ok:
        health.pop(slug, None)
        return RECOVERED if was_broken else None

    if was_broken:
        # Leave the entry untouched so a long outage does not churn the state file.
        return None

    failures = int(entry.get("consecutive_failures") or 0) + 1
    entry["consecutive_failures"] = failures
    entry["last_error"] = error[:300]

    transition = None
    if not was_broken and failures >= FAILURE_THRESHOLD:
        entry["status"] = BROKEN
        entry["broken_since"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        transition = BROKEN

    health[slug] = entry
    return transition
