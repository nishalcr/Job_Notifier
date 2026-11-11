"""
Daily digest queue.

Every run adds the new jobs it finds to seen_jobs/_digest.json (and marks them seen).
The first run at or after config.DIGEST_HOUR each day sends everything queued as one
digest. Jobs leave the queue only once the Telegram part holding them is delivered, so
a failed send is retried by the next run and nothing is sent twice.
"""

import json
import os
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import config
from notifier import send_digest
from state import job_key


def _queue_file() -> str:
    return os.path.join(config.SEEN_JOBS_DIR, "_digest.json")


def load_queue() -> dict[str, Any]:
    try:
        with open(_queue_file(), encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}
    return {"last_sent": data.get("last_sent", ""), "jobs": data.get("jobs", []), "issues": data.get("issues", [])}


def _save_queue(queue: dict[str, Any]) -> None:
    os.makedirs(config.SEEN_JOBS_DIR, exist_ok=True)
    tmp = _queue_file() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(queue, handle, indent=2, sort_keys=True)
    os.replace(tmp, _queue_file())


def _now() -> datetime:
    return datetime.now(ZoneInfo(config.ALERT_TIMEZONE))


def queue_jobs(company: str, slug: str, jobs: list[dict]) -> None:
    """Add jobs to the next digest; a job already queued is not added again."""
    queue = load_queue()
    queued = {(entry["slug"], job_key(entry["job"])) for entry in queue["jobs"]}
    for job in jobs:
        if (slug, job_key(job)) not in queued:
            queue["jobs"].append({"company": company, "slug": slug, "job": job})
            queued.add((slug, job_key(job)))
    _save_queue(queue)


def queue_issue(company: str, message: str) -> None:
    """Record a scraper problem for the digest's issues section."""
    queue = load_queue()
    queue["issues"].append({"company": company, "message": message, "at": _now().strftime("%b %d %I:%M %p")})
    _save_queue(queue)


async def send_digest_if_due(company_order: list[str] | None = None) -> bool:
    """Send the digest if it is past DIGEST_HOUR and none was sent today. Returns True if sent."""
    now = _now()
    queue = load_queue()
    today = now.date().isoformat()
    if now.hour < config.DIGEST_HOUR or queue["last_sent"] == today:
        return False

    # Group by company, in the configured company order, then queue order.
    rank = {slug: index for index, slug in enumerate(company_order or [])}
    groups: dict[str, list[dict]] = {}
    for entry in sorted(queue["jobs"], key=lambda e: rank.get(e["slug"], len(rank))):
        groups.setdefault(entry["company"], []).append(entry["job"])
    total = len(queue["jobs"])
    print(f"[digest] Sending daily digest: {total} job(s), {len(queue['issues'])} issue(s)")

    def on_delivered(company: str, jobs: list[dict]) -> None:
        # Saved per part, so a run that dies mid-send never re-sends a delivered part.
        sent = {job_key(job) for job in jobs}
        current = load_queue()
        current["jobs"] = [
            e for e in current["jobs"] if not (e["company"] == company and job_key(e["job"]) in sent)
        ]
        _save_queue(current)

    delivered, issues_sent = await send_digest(
        list(groups.items()), [f"{i['company']}: {i['message']}" for i in queue["issues"]], now, on_delivered
    )
    queue = load_queue()
    if issues_sent:
        queue["issues"] = []
    if delivered == total and issues_sent:
        queue["last_sent"] = today
    _save_queue(queue)
    if queue["last_sent"] != today:
        print(f"[digest] {total - delivered} job(s) not delivered; the next run retries")
        return False
    return True
