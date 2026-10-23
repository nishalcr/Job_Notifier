#!/usr/bin/env python3
"""
Multi-company jobs notifier.
Scrapes configured careers pages and sends Telegram alerts for newly seen jobs.
"""

import argparse
import asyncio
import sys
import time

from playwright.async_api import async_playwright

import config
from details import add_job_details
from health import BROKEN, load_health, record_result, save_health
from notifier import send_error, send_plain, send_run_summary, verify_bot
from runner import LAST_ERRORS, collect_jobs
from state import (
    filter_new_jobs,
    is_seen_elsewhere,
    job_key,
    load_seen_jobs,
    mark_jobs_seen,
    passes_title_filters,
    recent_title_keys,
    title_key,
)

# A job whose title this company already posted within this many days is not re-alerted.
REPEAT_TITLE_DAYS = 7


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape configured company career sites and send alerts.")
    parser.add_argument(
        "--company",
        action="append",
        dest="companies",
        help="Company slug to scrape. Repeat or pass a comma-separated list.",
    )
    return parser.parse_args()


async def _run_company_scrape(browser, slug: str, pending: list) -> tuple[bool, str]:
    """
    Scrape one company. Returns (ok, error message).

    Jobs to alert on are appended to pending as (runtime config, jobs); the run sends
    them all in one message at the end.
    """
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
        # Jobs another adapter for the same employer queued earlier in this run.
        shares = runtime_config.definition.shares_jobs_with
        queued_elsewhere = {
            job_key(job) for queued_config, jobs in pending if queued_config.slug in shares for job in jobs
        }
        for job in new_jobs:
            key = title_key(job.get("title", ""))
            if not passes_title_filters(job.get("title", ""), runtime_config):
                skipped.append(job)
            elif is_seen_elsewhere(job, shares) or job_key(job) in queued_elsewhere:
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
            print(f"[{runtime_config.slug}] Queued {len(to_alert)} job(s) for this run's message:")
            for job in to_alert:
                print(f"  - {job['title']}")
            pending.append((runtime_config, to_alert))
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


async def _send_pending(pending: list) -> None:
    """Send the run's queued jobs as one message; jobs are marked seen once delivered."""
    if not pending:
        return
    by_name = {runtime_config.display_name: runtime_config for runtime_config, _ in pending}
    total = sum(len(jobs) for _, jobs in pending)
    print(f"[scraper] Sending {total} job(s) to Telegram in one message...")
    delivered = await send_run_summary(
        [(runtime_config.display_name, jobs) for runtime_config, jobs in pending],
        # Saved the moment each part is sent, so a run that dies part-way through
        # never re-sends what it already delivered.
        on_delivered=lambda name, jobs: mark_jobs_seen(by_name[name], jobs),
    )
    if delivered < total:
        print(f"[scraper] {total - delivered} job(s) not delivered; they will be retried next run")


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
            pending = []
            for slug in requested_companies:
                ok, error = await _run_company_scrape(browser, slug, pending)
                if not ok:
                    failed_companies.append(slug)
                await _report_health(health, slug, ok, error)
            try:
                await add_job_details(browser, [job for _, jobs in pending for job in jobs])
            except Exception as exc:
                print(f"[details] Skipped job details: {exc}")
            await _send_pending(pending)
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
