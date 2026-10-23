"""Telegram notification sender for the multi-company jobs notifier."""

import asyncio
from datetime import datetime
from typing import Callable
from zoneinfo import ZoneInfo

import httpx

import config

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"

# Telegram rejects messages over 4096 characters; leave room for escaping.
MAX_MESSAGE_CHARS = 3800
MAX_SEND_ATTEMPTS = 3
MAX_RETRY_AFTER_SECONDS = 60


async def send_run_summary(
    groups: list[tuple[str, list[dict]]],
    on_delivered: Callable[[str, list[dict]], None] | None = None,
) -> int:
    """
    Send all of a run's new jobs as one message, grouped by company.

    groups is [(company name, jobs), ...]. A run with more than fits in one Telegram
    message is split into numbered parts. on_delivered(company name, jobs) is called
    for each part as soon as it is sent, so callers can mark those jobs seen.
    Returns the number of jobs delivered.
    """
    total = sum(len(jobs) for _, jobs in groups)
    if not total:
        return 0

    now = datetime.now(ZoneInfo(config.ALERT_TIMEZONE))
    stamp = f"{now:%b} {now.day}, {now:%I:%M %p}".replace(" 0", " ")
    title = f"🔔 *{total} new job{'s' if total != 1 else ''}* · {_escape_md(stamp)}"

    # Build every part first, so each can be numbered "(1/3)".
    parts: list[tuple[list[str], dict[str, list[dict]]]] = []
    lines: list[str] = []
    part_jobs: dict[str, list[dict]] = {}
    size = len(title) + 20

    def start_part() -> None:
        nonlocal lines, part_jobs, size
        if part_jobs:
            parts.append((lines, part_jobs))
        lines, part_jobs, size = [], {}, len(title) + 20

    started: set[str] = set()
    for company_name, jobs in groups:
        for job in jobs:
            entry = _summary_entry(job)
            if part_jobs and size + len(entry) + 60 > MAX_MESSAGE_CHARS:
                start_part()
            if company_name not in part_jobs:
                # A company split across parts is marked "(cont.)" in the later part.
                count = "\\(cont\\.\\)" if company_name in started else f"· {len(jobs)}"
                lines.extend(["", f"*{_escape_md(company_name)}* {count}"])
                size += len(lines[-1]) + 2
                started.add(company_name)
            lines.append(entry)
            size += len(entry) + 1
            part_jobs.setdefault(company_name, []).append(job)
    start_part()

    delivered = 0
    for index, (part_lines, jobs_by_company) in enumerate(parts, 1):
        if index > 1:
            await asyncio.sleep(0.5)
        suffix = f" \\({index}/{len(parts)}\\)" if len(parts) > 1 else ""
        text = "\n".join([title + suffix, *part_lines])
        if not await _send_message(text, parse_mode="MarkdownV2"):
            continue
        for company_name, jobs in jobs_by_company.items():
            delivered += len(jobs)
            if on_delivered:
                on_delivered(company_name, jobs)
    return delivered


def _summary_entry(job: dict) -> str:
    """One job in a run summary: linked title, then location and post date."""
    title = _escape_md(job.get("title", "Unknown Position"))
    url = job.get("url", "")
    line = f"• [{title}]({_escape_url(url)})" if url else f"• {title}"
    details = [job.get("location", ""), _format_posted(job.get("source_posted", ""))]
    details = [_escape_md(detail) for detail in details if detail]
    if details:
        line += "\n    " + " · ".join(details)
    return line


async def send_error(company_name: str, error_msg: str) -> bool:
    """Send an error notification."""
    message = f"⚠️ *{_escape_md(company_name)} Jobs Scraper Error*\n\n`{_escape_md(error_msg)}`"
    return await _send_message(message, parse_mode="MarkdownV2")


async def send_plain(text: str) -> bool:
    """Send a plain text message (no Markdown)."""
    return await _send_message(text, parse_mode="")


async def verify_bot() -> bool:
    """Verify the Telegram bot token is valid. Returns True if OK."""
    if not config.TELEGRAM_BOT_TOKEN:
        return False
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{TELEGRAM_API}/getMe")
            return resp.status_code == 200 and resp.json().get("ok", False)
    except httpx.HTTPError:
        return False


async def _send_message(text: str, parse_mode: str = "MarkdownV2") -> bool:
    """Low-level Telegram sendMessage call with rate-limit retries."""
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[notifier] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set - skipping notification.")
        return False

    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": text,
        "link_preview_options": {"is_disabled": True},
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for attempt in range(1, MAX_SEND_ATTEMPTS + 1):
                resp = await client.post(f"{TELEGRAM_API}/sendMessage", json=payload)
                if resp.status_code == 200 and resp.json().get("ok"):
                    return True
                print(f"[notifier] Telegram API error: {resp.status_code} - {resp.text}")

                if resp.status_code == 429 and attempt < MAX_SEND_ATTEMPTS:
                    retry_after = _retry_after_seconds(resp)
                    print(f"[notifier] Rate limited; retrying in {retry_after}s")
                    await asyncio.sleep(retry_after)
                    continue

                if resp.status_code == 400 and payload.get("parse_mode"):
                    # Formatting rejected: resend once as plain text.
                    payload.pop("parse_mode")
                    payload["text"] = text.replace("*", "").replace("`", "").replace("\\", "")
                    continue

                return False
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout) as exc:
        # The request never reached Telegram, so the job is retried next run.
        print(f"[notifier] Could not reach Telegram: {exc}")
    except httpx.HTTPError as exc:
        # The request was sent but the reply was lost (e.g. read timeout). Telegram may
        # already have posted the message, so count it as sent rather than risk a duplicate.
        print(f"[notifier] No reply from Telegram ({exc!r}); treating the message as sent")
        return True
    return False


def _retry_after_seconds(resp: httpx.Response) -> int:
    try:
        retry_after = int(resp.json().get("parameters", {}).get("retry_after", 1))
    except (ValueError, TypeError, AttributeError):
        retry_after = 1
    return max(1, min(retry_after, MAX_RETRY_AFTER_SECONDS))


def _format_posted(value: str) -> str:
    """Normalize a source post date: ISO dates become "Oct 22"; other text is kept."""
    value = str(value or "").strip()
    if value.lower().startswith("posted "):
        value = value[len("posted "):].strip()
    if len(value) > 10 and value[4:5] == "-" and "T" in value:
        value = value.split("T", 1)[0]
    try:
        posted = datetime.strptime(value, "%Y-%m-%d")
        return f"{posted:%b} {posted.day}"
    except ValueError:
        return value


def _escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!\\"
    return "".join(f"\\{ch}" if ch in special else ch for ch in str(text))


def _escape_url(url: str) -> str:
    """Escape a URL for the (...) part of a MarkdownV2 link."""
    return str(url).replace("\\", "\\\\").replace(")", "\\)")
