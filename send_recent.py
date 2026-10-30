#!/usr/bin/env python3
"""
Catch-up sends, outside the regular 10-minute runs.

Default mode: send matching jobs posted on a given day, whether or not they were
seen before (e.g. after a company is first seeded). Does not change seen state.

--unseen mode: read deeper than a regular run and send every matching job that is
not in the seen store yet (e.g. jobs a filter fix now matches but that are older
than a regular run's first pages). Sent jobs are marked seen, so they never repeat.
"""

import argparse
import asyncio
from datetime import date, datetime
from zoneinfo import ZoneInfo

from playwright.async_api import async_playwright

import config
from notifier import send_run_summary
from runner import collect_jobs
from details import add_job_details
from state import is_seen_elsewhere, job_key, load_seen_jobs, mark_jobs_seen, passes_title_filters, posted_date



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", action="append", dest="companies", help="Company slug(s), comma-separated.")
    parser.add_argument("--posted-on", help="YYYY-MM-DD (default: today in ALERT_TIMEZONE).")
    parser.add_argument("--pages", type=int, default=10, help="Result pages to scan per company (default 10).")
    parser.add_argument("--unseen", action="store_true", help="Send matching jobs not seen before (any post date) and mark them seen.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    today = datetime.now(ZoneInfo(config.ALERT_TIMEZONE)).date()
    target = date.fromisoformat(args.posted_on) if args.posted_on else today
    slugs = config.get_selected_company_slugs(args.companies)
    if args.unseen:
        print(f"[send-recent] Matching jobs not seen before, for: {', '.join(slugs)}")
    else:
        print(f"[send-recent] Jobs posted on {target} for: {', '.join(slugs)}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--disable-blink-features=AutomationControlled"])
        try:
            for slug in slugs:
                runtime_config = config.get_company_runtime(slug)
                pages = min(args.pages, runtime_config.full_scrape_max_pages)
                jobs = await collect_jobs(browser, runtime_config, pages)
                if args.unseen:
                    seen = load_seen_jobs(slug)
                    shares = runtime_config.definition.shares_jobs_with
                    matches = [
                        job
                        for job in jobs
                        if passes_title_filters(job.get("title", ""), runtime_config)
                        and job_key(job) not in seen
                        and not is_seen_elsewhere(job, shares)
                    ]
                else:
                    matches = [
                        job
                        for job in jobs
                        if passes_title_filters(job.get("title", ""), runtime_config)
                        and posted_date(job.get("posted", ""), today) == target
                    ]
                print(f"[send-recent] {runtime_config.display_name}: {len(matches)} matching job(s)")
                for job in matches:
                    print(f"  - {job['title']}")
                    job.setdefault("source_posted", job.get("posted", ""))
                if not matches:
                    continue
                await add_job_details(browser, matches)
                on_delivered = (lambda name, sent, rc=runtime_config: mark_jobs_seen(rc, sent)) if args.unseen else None
                delivered = await send_run_summary([(runtime_config.display_name, matches)], on_delivered)
                print(f"[send-recent] Delivered {delivered}/{len(matches)}")
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
