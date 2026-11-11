"""Daily digest queue: sent once a day after DIGEST_HOUR, never twice, nothing dropped."""

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

import config
import digest
import notifier


@pytest.fixture
def clock(seen_dir, monkeypatch):
    """Set the digest's "now" with clock(day, hour)."""
    current = {}

    def set_time(day, hour):
        current["now"] = datetime(2026, 11, day, hour, tzinfo=ZoneInfo(config.ALERT_TIMEZONE))

    monkeypatch.setattr(digest, "_now", lambda: current["now"])
    monkeypatch.setattr(config, "DIGEST_HOUR", 8)
    return set_time


@pytest.fixture
def telegram(monkeypatch):
    """Captured Telegram messages; set fail_on to message numbers that should fail."""
    box = {"messages": [], "fail_on": set()}

    async def fake_send(text, parse_mode="MarkdownV2"):
        box["messages"].append(text)
        return len(box["messages"]) not in box["fail_on"]

    monkeypatch.setattr(notifier, "_send_message", fake_send)
    return box


def jobs(n, prefix="j"):
    return [{"key": f"{prefix}{i}", "title": f"Software Engineer {i}", "url": f"https://x/{i}"} for i in range(n)]


def test_digest_waits_for_the_hour_then_sends_once_a_day(clock, telegram):
    digest.queue_jobs("Google", "google", jobs(3))
    clock(12, 7)
    assert not asyncio.run(digest.send_digest_if_due())
    assert telegram["messages"] == []

    clock(12, 8)
    assert asyncio.run(digest.send_digest_if_due())
    assert "3 new jobs" in telegram["messages"][0]
    assert digest.load_queue()["jobs"] == []

    digest.queue_jobs("Google", "google", jobs(1, "later"))
    clock(12, 15)
    assert not asyncio.run(digest.send_digest_if_due())
    assert len(telegram["messages"]) == 1

    clock(13, 8)
    assert asyncio.run(digest.send_digest_if_due())
    assert "1 new job*" in telegram["messages"][1]


def test_queueing_the_same_job_twice_sends_it_once(clock, telegram):
    digest.queue_jobs("Google", "google", jobs(2))
    digest.queue_jobs("Google", "google", jobs(2))
    assert len(digest.load_queue()["jobs"]) == 2


def test_failed_part_is_retried_next_run_without_resending_delivered_parts(clock, telegram):
    digest.queue_jobs("Amazon", "amazon", jobs(200))
    telegram["fail_on"] = {2}
    clock(12, 8)
    assert not asyncio.run(digest.send_digest_if_due())
    remaining = len(digest.load_queue()["jobs"])
    assert 0 < remaining < 200

    telegram["fail_on"] = set()
    first_try = len(telegram["messages"])
    clock(12, 8)
    assert asyncio.run(digest.send_digest_if_due())
    assert len(telegram["messages"]) - first_try == 1  # only the failed part again
    assert digest.load_queue()["jobs"] == []


def test_empty_day_and_issues_still_send_a_message(clock, telegram):
    clock(12, 9)
    digest.queue_issue("Cisco", "Broken for 3 consecutive runs")
    assert asyncio.run(digest.send_digest_if_due())
    text = telegram["messages"][0].replace("\\", "")
    assert "No new matching jobs" in text and "Cisco: Broken" in text
    assert digest.load_queue()["issues"] == []
