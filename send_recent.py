#!/usr/bin/env python3
"""
Send matching jobs posted on a given day to Telegram, whether or not they were seen before.

For catching up on jobs that were marked seen without an alert (for example when
a company is first seeded). Does not change the seen-jobs state.
"""

import argparse
import asyncio
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

import config
import scraper
from runner import collect_jobs
from state import passes_title_filters

MONTH_DATE_RE = re.compile(r"[A-Z][a-z]{2,8} \d{1,2}, \d{4}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", action="append", dest="companies", help="Company slug(s), comma-separated.")
    parser.add_argument("--posted-on", help="YYYY-MM-DD (default: today in ALERT_TIMEZONE).")
    parser.add_argument("--pages", type=int, default=10, help="Result pages to scan per company (default 10).")
    return parser.parse_args()


def posted_date(value: str, today: date) -> date | None:
    """Read a job's source post date: ISO dates, "Sep 29, 2026", or "Posted Today/Yesterday"."""
    text = str(value or "").strip()
    lowered = text.lower().removeprefix("posted ").strip()
    if lowered == "today":
        return today
    if lowered == "yesterday":
        return today - timedelta(days=1)
    if re.match(r"\d{4}-\d{2}-\d{2}", text):
        return date.fromisoformat(text[:10])
    match = MONTH_DATE_RE.search(text)
    if match:
        for fmt in ("%b %d, %Y", "%B %d, %Y"):
            try:
                return datetime.strptime(match.group(0), fmt).date()
            except ValueError:
                continue
    return None


async def main() -> None:
    args = parse_args()
    today = datetime.now(ZoneInfo(config.ALERT_TIMEZONE)).date()
    target = date.fromisoformat(args.posted_on) if args.posted_on else today
    slugs = config.get_selected_company_slugs(args.companies)
    print(f"[send-recent] Jobs posted on {target} for: {', '.join(slugs)}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        try:
            for slug in slugs:
                runtime_config = config.get_company_runtime(slug)
                pages = min(args.pages, runtime_config.full_scrape_max_pages)
                jobs = await collect_jobs(browser, runtime_config, pages)
                matches = [
                    job
                    for job in jobs
                    if passes_title_filters(job.get("title", ""), runtime_config)
                    and posted_date(job.get("posted", ""), today) == target
                ]
                print(f"[send-recent] {runtime_config.display_name}: {len(matches)} matching job(s) posted on {target}")
                for job in matches:
                    print(f"  - {job['title']}")
                    job["source_posted"] = job.get("posted", "")
                if matches:
                    delivered = await scraper._send_alerts(runtime_config.display_name, matches)
                    print(f"[send-recent] Delivered {len(delivered)}/{len(matches)}")
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
