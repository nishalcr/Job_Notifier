#!/usr/bin/env python3
"""
Multi-company jobs notifier.
Scrapes configured careers pages and sends Telegram alerts for newly seen jobs.
"""

import argparse
import asyncio
import sys
import time
from typing import Callable

from playwright.async_api import async_playwright

import config
from health import BROKEN, load_health, record_result, save_health
from notifier import (
    send_error,
    send_job_alert_for_company,
    send_job_digest,
    send_plain,
    send_run_header,
    verify_bot,
)
from runner import LAST_ERRORS, collect_jobs
from state import (
    filter_new_jobs,
    is_seen_elsewhere,
    load_seen_jobs,
    mark_jobs_seen,
    passes_title_filters,
    recent_title_keys,
    title_key,
)

# More new jobs than this for one company in one run are sent as a digest.
DIGEST_THRESHOLD = 5

# A job whose title this company already posted within this many days is not re-alerted.
REPEAT_TITLE_DAYS = 7

# Whether this run already sent its separator message (sent only if the run has alerts).
_run_header_sent = False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape configured company career sites and send alerts.")
    parser.add_argument(
        "--company",
        action="append",
        dest="companies",
        help="Company slug to scrape. Repeat or pass a comma-separated list.",
    )
    return parser.parse_args()


async def _run_company_scrape(browser, slug: str) -> tuple[bool, str]:
    """Scrape one company. Returns (ok, error message)."""
    runtime_config = None

    try:
        runtime_config = config.get_company_runtime(slug)
        unique_jobs = await collect_jobs(browser, runtime_config, runtime_config.max_pages)

        if not unique_jobs:
            if runtime_config.definition.allow_empty_results:
                print(
                    f"[scraper] WARNING: No jobs were extracted for "
                    f"{runtime_config.display_name}. Treating as non-fatal for this company."
                )
                return True, ""

            print(f"[scraper] No jobs were extracted for {runtime_config.display_name}.")
            return False, LAST_ERRORS.get(slug) or "No jobs extracted. The page structure may have changed."

        new_jobs = filter_new_jobs(runtime_config, unique_jobs)
        print(f"[{runtime_config.slug}] New jobs (not seen before): {len(new_jobs)}")

        to_alert = []
        skipped = []
        # Some employers (e.g. Capital One) post many openings with the same generic
        # title; alert on a title once per REPEAT_TITLE_DAYS per company.
        recent_titles = recent_title_keys(runtime_config, REPEAT_TITLE_DAYS)
        for job in new_jobs:
            key = title_key(job.get("title", ""))
            if not passes_title_filters(job.get("title", ""), runtime_config):
                skipped.append(job)
            elif is_seen_elsewhere(job, runtime_config.definition.shares_jobs_with):
                skipped.append(job)
            elif key in recent_titles:
                skipped.append(job)
            else:
                recent_titles.add(key)
                to_alert.append(job)
        if skipped:
            print(f"[{runtime_config.slug}] Skipped {len(skipped)} job(s) (title filter, already alerted or repeated title)")
        mark_jobs_seen(runtime_config, skipped)

        if to_alert:
            print(f"[{runtime_config.slug}] Sending {len(to_alert)} job(s) to Telegram...")
            for job in to_alert:
                print(f"  - {job['title']}")
            # Each job is saved as seen the moment its message is sent, so a run that
            # dies part-way through never re-sends what it already delivered.
            delivered = await _send_alerts(
                runtime_config.display_name,
                to_alert,
                on_delivered=lambda jobs: mark_jobs_seen(runtime_config, jobs),
            )
            if len(delivered) < len(to_alert):
                print(
                    f"[{runtime_config.slug}] {len(to_alert) - len(delivered)} alert(s) failed; "
                    "they will be retried next run"
                )
        else:
            print(f"[{runtime_config.slug}] No new jobs to notify.")

        print(
            f"[{runtime_config.slug}] Seen jobs database: "
            f"{len(load_seen_jobs(runtime_config.slug))} entries"
        )
        return True, ""
    except Exception as exc:
        print(f"[{slug}] Unexpected company failure: {exc}")
        return False, f"Unexpected error: {exc}"


async def _send_alerts(
    company_name: str,
    jobs: list[dict],
    on_delivered: Callable[[list[dict]], None] | None = None,
) -> list[dict]:
    """
    Send alerts one per job, or as a digest for bursts. Returns delivered jobs.

    on_delivered is called with the jobs of each message as soon as it is sent.
    """
    global _run_header_sent
    if not _run_header_sent:
        _run_header_sent = await send_run_header()

    if len(jobs) > DIGEST_THRESHOLD:
        return await send_job_digest(company_name, jobs, on_delivered)

    delivered = []
    for index, job in enumerate(jobs):
        if index:
            await asyncio.sleep(0.5)
        if await send_job_alert_for_company(company_name, job):
            delivered.append(job)
            if on_delivered:
                on_delivered([job])
    return delivered


async def _report_health(health: dict, slug: str, ok: bool, error: str) -> None:
    transition = record_result(health, slug, ok, error)
    if transition is None:
        return

    try:
        company_name = config.get_company_runtime(slug).display_name
    except Exception:
        company_name = slug

    if transition == BROKEN:
        failures = health[slug]["consecutive_failures"]
        print(f"[health] {company_name} marked broken after {failures} consecutive failures")
        await send_error(company_name, f"Broken for {failures} consecutive runs. Last error: {error}")
    else:
        print(f"[health] {company_name} recovered")
        await send_plain(f"✅ {company_name} scraper recovered.")


async def run_scraper(selected_companies: list[str] | None = None) -> None:
    """Main scraper entry point."""
    global _run_header_sent
    _run_header_sent = False
    start_time = time.time()
    requested_companies = config.get_selected_company_slugs(selected_companies)

    print("=" * 60)
    print("[scraper] Multi-company jobs notifier starting")
    print(f"[scraper] Companies: {', '.join(requested_companies)}")
    print("=" * 60)

    bot_ok = await verify_bot()
    if not bot_ok:
        print("[scraper] WARNING: Telegram bot verification failed. Notifications may not work.")
        if not config.TELEGRAM_BOT_TOKEN:
            print("[scraper] TELEGRAM_BOT_TOKEN is not set.")
        if not config.TELEGRAM_CHAT_ID:
            print("[scraper] TELEGRAM_CHAT_ID is not set.")

    failed_companies = []
    health = load_health()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
        try:
            for slug in requested_companies:
                ok, error = await _run_company_scrape(browser, slug)
                if not ok:
                    failed_companies.append(slug)
                await _report_health(health, slug, ok, error)
        finally:
            await browser.close()
            save_health(health)

    elapsed = time.time() - start_time
    print(f"\n[scraper] Run completed in {elapsed:.1f}s")

    if failed_companies:
        print(f"[scraper] Failed companies: {', '.join(failed_companies)}")
        sys.exit(1)


def main() -> None:
    args = parse_args()
    asyncio.run(run_scraper(args.companies))


if __name__ == "__main__":
    main()
