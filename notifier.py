"""Telegram notification sender for the multi-company jobs notifier."""

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

import config

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"

# Telegram rejects messages over 4096 characters; leave room for escaping.
MAX_MESSAGE_CHARS = 3800
MAX_SEND_ATTEMPTS = 3
MAX_RETRY_AFTER_SECONDS = 60


async def send_job_alert_for_company(company_name: str, job: dict) -> bool:
    """Send a single job notification to Telegram. Returns True on success."""
    title = job.get("title", "Unknown Position")
    team = job.get("team", "")
    location = job.get("location", "")
    posted = _format_posted(job.get("source_posted", ""))
    role_number = job.get("job_id") or job.get("role_number") or job.get("key", "")
    weekly_hours = job.get("weekly_hours", "")
    url = job.get("url", "")
    escaped_company = _escape_md(company_name)

    lines = [
        f"🔔 *New {escaped_company} Job*",
        "",
        f"📌 *{_escape_md(title)}*",
    ]
    if team:
        lines.append(f"🏢 {_escape_md(team)}")
    if location:
        lines.append(f"📍 {_escape_md(location)}")
    if posted:
        lines.append(f"🗓 Posted {_escape_md(posted)}")
    if role_number:
        lines.append(f"🆔 `{_escape_md(role_number)}`")
    if weekly_hours:
        lines.append(f"⏱ {_escape_md(weekly_hours)}")
    if url:
        lines.extend(["", f"[Apply on {escaped_company} Careers]({_escape_url(url)})"])

    return await _send_message("\n".join(lines), parse_mode="MarkdownV2")


async def send_job_digest(company_name: str, jobs: list[dict]) -> list[dict]:
    """
    Send several jobs as compact digest message(s).

    Returns the jobs whose message was delivered, so callers only mark those seen.
    """
    header = f"🔔 *{len(jobs)} new {_escape_md(company_name)} jobs*"
    delivered = []
    chunk_lines: list[str] = []
    chunk_jobs: list[dict] = []

    async def flush() -> None:
        if not chunk_jobs:
            return
        text = "\n".join([header, "", *chunk_lines])
        if await _send_message(text, parse_mode="MarkdownV2"):
            delivered.extend(chunk_jobs)
        chunk_lines.clear()
        chunk_jobs.clear()

    for job in jobs:
        line = f"• [{_escape_md(job.get('title', 'Unknown Position'))}]({_escape_url(job.get('url', ''))})"
        if job.get("location"):
            line += f" — {_escape_md(job['location'])}"
        if chunk_jobs and len(header) + sum(len(x) + 1 for x in chunk_lines) + len(line) > MAX_MESSAGE_CHARS:
            await flush()
            await asyncio.sleep(0.5)
        chunk_lines.append(line)
        chunk_jobs.append(job)
    await flush()
    return delivered


async def send_run_header() -> bool:
    """Separator sent before the first alert of a run, so each run's alerts stand apart."""
    now = datetime.now(ZoneInfo(config.ALERT_TIMEZONE))
    stamp = f"{now:%b} {now.day}, {now:%I:%M %p}".replace(" 0", " ")
    divider = "━━━━━━━━━━━━━━━━━━━━"
    return await _send_message(f"{divider}\n🕐 New jobs · {stamp}\n{divider}", parse_mode="")


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
    except httpx.HTTPError as exc:
        print(f"[notifier] HTTP error sending Telegram message: {exc}")
    return False


def _retry_after_seconds(resp: httpx.Response) -> int:
    try:
        retry_after = int(resp.json().get("parameters", {}).get("retry_after", 1))
    except (ValueError, TypeError, AttributeError):
        retry_after = 1
    return max(1, min(retry_after, MAX_RETRY_AFTER_SECONDS))


def _format_posted(value: str) -> str:
    """Normalize a source post date: ISO timestamps become YYYY-MM-DD."""
    value = str(value or "").strip()
    if value.lower().startswith("posted "):
        value = value[len("posted "):].strip()
    if len(value) > 10 and value[4:5] == "-" and "T" in value:
        value = value.split("T", 1)[0]
    return value


def _escape_md(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!\\"
    return "".join(f"\\{ch}" if ch in special else ch for ch in str(text))


def _escape_url(url: str) -> str:
    """Escape a URL for the (...) part of a MarkdownV2 link."""
    return str(url).replace("\\", "\\\\").replace(")", "\\)")
